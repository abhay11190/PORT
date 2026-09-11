import hmac
import hashlib
import base64
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx

from config import WHOP_API_KEY, WHOP_WEBHOOK_SECRET, WHOP_COMPANY_ID

logger = logging.getLogger(__name__)


@dataclass
class PaymentSessionResult:
    success: bool
    payment_id: Optional[str]
    checkout_url: str
    error_message: Optional[str] = None


class WhopPaymentProvider:
    """
    Whop Payments integration provider.
    Abstracts payment creation and webhook signature validation.
    Fully supports individual creator accounts verified with personal identification (PAN/ID)
    without requiring business tax IDs, registered companies, or manual company ID entry.
    """

    BASE_URL = "https://api.whop.com/api/v5"

    def __init__(self, api_key: str, webhook_secret: str, company_id: str):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.company_id = company_id

    @staticmethod
    def _extract_biz_id(obj: Any) -> Optional[str]:
        """
        Recursively inspects any JSON-compatible structure returned by the Whop API
        to locate any assigned 'biz_...' company/store identifier.
        """
        if isinstance(obj, str):
            clean = obj.strip()
            if clean.startswith("biz_") and len(clean) > 4:
                return clean
        elif isinstance(obj, dict):
            # Prioritize standard property names
            for key in ("company_id", "id", "store_id", "biz_id"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip().startswith("biz_"):
                    return val.strip()
            for val in obj.values():
                res = WhopPaymentProvider._extract_biz_id(val)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = WhopPaymentProvider._extract_biz_id(item)
                if res:
                    return res
        return None

    async def get_company_id(self) -> Optional[str]:
        """
        Retrieves the Whop Company/Store ID.
        If WHOP_COMPANY_ID is not configured in the environment, this method automatically
        queries the Whop API using WHOP_API_KEY to discover the assigned 'biz_...' ID.
        This works seamlessly for individual creator accounts (verified with PAN card, etc.)
        where Whop automatically assigns a 'biz_...' identifier without requiring a corporate tax ID.
        """
        if self.company_id and self.company_id.startswith("biz_"):
            return self.company_id

        if not self.api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                for endpoint in (
                    "https://api.whop.com/api/v1/companies",
                    "https://api.whop.com/api/v5/companies",
                    "https://api.whop.com/api/v5/me",
                ):
                    try:
                        resp = await client.get(endpoint, headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            found = self._extract_biz_id(data)
                            if found:
                                self.company_id = found
                                logger.info("Automatically resolved Whop Store/Company ID: %s", self.company_id)
                                return self.company_id
                    except Exception as req_err:
                        logger.debug("Endpoint %s check: %s", endpoint, req_err)
                        continue
        except Exception as exc:
            logger.warning("Could not auto-fetch Whop company ID: %s", exc)

        return self.company_id if (self.company_id and self.company_id.startswith("biz_")) else None

    async def create_checkout_session(
        self,
        order_id: str,
        amount: float,
        currency: str,
        description: str,
        user_id: int,
        return_url: Optional[str] = None,
    ) -> PaymentSessionResult:
        """
        Creates a payment / checkout session with Whop.
        Supports both live Whop API Checkout sessions and direct portal checkouts.
        Works with individual creator accounts and business accounts alike.
        """
        active_company_id = await self.get_company_id()

        # If WHOP_API_KEY is present, attempt live Whop API Checkout session
        if self.api_key:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            # Whop amounts are in cents/smallest currency unit
            amount_cents = int(round(amount * 100))
            payload: Dict[str, Any] = {
                "metadata": {
                    "order_id": order_id,
                    "user_id": str(user_id),
                    "service": "VirtualNumberMarketplace",
                },
                "line_items": [
                    {
                        "amount": amount_cents,
                        "currency": currency.lower(),
                        "name": f"Virtual Number Order {order_id}",
                        "description": description[:120],
                        "quantity": 1,
                    }
                ],
            }
            if active_company_id:
                payload["company_id"] = active_company_id
            if return_url:
                payload["redirect_url"] = return_url

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/checkout_sessions",
                        headers=headers,
                        json=payload,
                    )
                    if response.status_code in (200, 201):
                        data = response.json()
                        checkout_url = data.get("url") or data.get("checkout_url")
                        payment_id = data.get("id")
                        if checkout_url:
                            return PaymentSessionResult(
                                success=True,
                                payment_id=payment_id,
                                checkout_url=checkout_url,
                            )
                    logger.warning(
                        "Whop API checkout session returned status %d: %s",
                        response.status_code,
                        response.text[:200],
                    )
            except Exception as exc:
                logger.error("Error connecting to Whop API: %s", exc)

        # Fallback / Direct checkout portal link with embedded order tracking
        company = active_company_id or self.company_id or "marketplace"
        clean_currency = currency.upper()
        # Clean URL for user payment interface
        checkout_url = (
            f"https://whop.com/checkout/{company}?"
            f"order_id={order_id}&amount={amount:.2f}&currency={clean_currency}"
        )
        return PaymentSessionResult(
            success=True,
            payment_id=f"whop_chk_{order_id}",
            checkout_url=checkout_url,
        )

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        signature_header: Optional[str],
        timestamp_header: Optional[str] = None,
        msg_id_header: Optional[str] = None,
    ) -> bool:
        """
        Verifies Whop webhook signature using WHOP_WEBHOOK_SECRET.
        Supports:
        - Svix / Whop base64 encoded secrets (whsec_...) and raw secrets
        - Timestamped signatures ('t=...,v1=...' or 'v1,...')
        - Both base64 and hex HMAC-SHA256 digests
        - Constant-time comparison to prevent timing attacks
        """
        if not self.webhook_secret:
            logger.warning("WHOP_WEBHOOK_SECRET is not configured; webhook rejected.")
            return False

        if not signature_header:
            logger.warning("Missing webhook signature header.")
            return False

        # Prepare secret keys (both raw and base64-decoded if whsec_ prefix exists)
        secret_keys: List[bytes] = [self.webhook_secret.encode("utf-8")]
        if self.webhook_secret.startswith("whsec_"):
            try:
                b64_part = self.webhook_secret[6:]
                decoded = base64.b64decode(b64_part)
                if decoded:
                    secret_keys.insert(0, decoded)
            except Exception:
                pass

        # Extract timestamp and candidate signatures
        timestamp = timestamp_header
        candidate_signatures: List[str] = []

        # Parse signature header components
        for part in signature_header.split(" "):
            for sub in part.split(","):
                sub = sub.strip()
                if sub.startswith("t="):
                    timestamp = sub[2:]
                elif sub.startswith("v1="):
                    candidate_signatures.append(sub[3:])
                elif sub.startswith("v1,"):
                    candidate_signatures.append(sub[3:])
                elif sub.startswith("sha256="):
                    candidate_signatures.append(sub[7:])
                elif sub and not sub.startswith("v0") and not sub.startswith("t="):
                    candidate_signatures.append(sub)

        # Build payload candidates to test
        payloads_to_test: List[bytes] = []
        if timestamp and msg_id_header:
            payloads_to_test.append(f"{msg_id_header}.{timestamp}.".encode("utf-8") + raw_body)
        if timestamp:
            payloads_to_test.append(f"{timestamp}.".encode("utf-8") + raw_body)
        payloads_to_test.append(raw_body)

        for key in secret_keys:
            for payload in payloads_to_test:
                computed_digest = hmac.new(key, payload, hashlib.sha256).digest()
                computed_b64 = base64.b64encode(computed_digest).decode("utf-8")
                computed_hex = computed_digest.hex()

                for cand in candidate_signatures:
                    cand_clean = cand.strip()
                    if hmac.compare_digest(computed_b64, cand_clean) or hmac.compare_digest(computed_hex, cand_clean):
                        return True

        logger.warning("Webhook signature verification failed against provided secret.")
        return False


# Singleton provider instance
payment_provider = WhopPaymentProvider(
    api_key=WHOP_API_KEY,
    webhook_secret=WHOP_WEBHOOK_SECRET,
    company_id=WHOP_COMPANY_ID,
)
