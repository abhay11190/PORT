import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import uvicorn

from config import (
    PORT,
    BOT_TOKEN,
    WHOP_API_KEY,
    WHOP_WEBHOOK_SECRET,
    validate_config,
)
from database import (
    init_db,
    is_event_processed,
    record_processed_event,
    fulfill_order_and_credit_seller,
    mark_order_failed,
    get_order_by_order_id,
)
from payments import payment_provider
from bot import build_telegram_application, notify_user_order_fulfilled

# Configure logging format
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("marketplace")

# Global reference to Telegram application
telegram_app = None
bot_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager:
    Initializes database tables, boots Telegram bot in background polling,
    and handles graceful shutdown on container termination.
    """
    global telegram_app, bot_task

    logger.info("Initializing Marketplace Database...")
    init_db()

    # Run startup configuration checks and diagnostics
    validate_config(strict_bot_token=False)

    # Check Whop credentials and log clear startup errors if missing
    if not WHOP_API_KEY:
        logger.error(
            "❌ [STARTUP ERROR] WHOP_API_KEY is missing! "
            "Set WHOP_API_KEY in environment variables to enable payments and auto-discover your store's biz_... ID."
        )
    if not WHOP_WEBHOOK_SECRET:
        logger.error(
            "❌ [STARTUP ERROR] WHOP_WEBHOOK_SECRET is missing! "
            "Set WHOP_WEBHOOK_SECRET in environment variables to verify incoming payment webhooks."
        )

    # Automatically discover Whop Store/Company ID via Whop API if WHOP_API_KEY is configured
    if WHOP_API_KEY:
        try:
            logger.info("Discovering Whop Store/Company ID (biz_...) via Whop API...")
            discovered_id = await payment_provider.get_company_id()
            if discovered_id:
                logger.info("✅ Whop Store ID automatically resolved: %s", discovered_id)
            else:
                logger.info("Whop Store ID will be resolved on first checkout request.")
        except Exception as exc:
            logger.warning("Whop Store ID discovery will be retried on checkout: %s", exc)

    # Start Telegram Bot alongside FastAPI Webhook server
    if BOT_TOKEN:
        logger.info("Starting Telegram Bot Application...")
        try:
            telegram_app = build_telegram_application()
            await telegram_app.initialize()
            await telegram_app.start()
            await telegram_app.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"],
            )
            logger.info("Telegram Bot started and actively polling for updates.")
        except Exception as exc:
            logger.error("Failed to start Telegram bot: %s", exc, exc_info=True)
    else:
        logger.warning(
            "BOT_TOKEN is not set! Running in webhook/API-only mode. "
            "Set BOT_TOKEN to enable the Telegram bot interface."
        )

    yield

    # Graceful Shutdown
    if telegram_app:
        logger.info("Stopping Telegram Bot...")
        try:
            if telegram_app.updater and telegram_app.updater.running:
                await telegram_app.updater.stop()
            if telegram_app.running:
                await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("Telegram Bot shut down cleanly.")
        except Exception as exc:
            logger.error("Error during Telegram bot shutdown: %s", exc)


app = FastAPI(
    title="Premium Virtual Number Marketplace API",
    description="Webhook server and backend for Telegram Virtual Number Marketplace",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint for Render Web Service monitoring.
    Returns: {"status": "ok"}
    """
    return {"status": "ok"}


@app.post("/webhooks/whop")
async def whop_webhook(request: Request):
    """
    Production-safe Whop Payment Webhook Endpoint.
    - Verifies raw HMAC-SHA256 signature using WHOP_WEBHOOK_SECRET.
    - Protects against replay attacks and duplicate deliveries with idempotency tracking.
    - Atomically updates order status, delivers purchased numbers, and credits seller wallets.
    """
    # 1. Read raw body for cryptographic signature verification
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty request payload",
        )

    # 2. Extract signature and headers from possible Whop signature formats
    signature = (
        request.headers.get("webhook-signature")
        or request.headers.get("whop-signature")
        or request.headers.get("x-whop-signature")
    )
    timestamp = (
        request.headers.get("webhook-timestamp")
        or request.headers.get("whop-timestamp")
        or request.headers.get("x-whop-timestamp")
    )
    msg_id = (
        request.headers.get("webhook-id")
        or request.headers.get("whop-id")
        or request.headers.get("x-whop-id")
    )

    # 3. Cryptographically verify signature if secret configured
    if WHOP_WEBHOOK_SECRET:
        if not signature or not payment_provider.verify_webhook_signature(
            raw_body=raw_body,
            signature_header=signature,
            timestamp_header=timestamp,
            msg_id_header=msg_id,
        ):
            logger.warning("Unauthorized webhook: Signature verification failed.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing webhook signature",
            )
    else:
        logger.warning(
            "WHOP_WEBHOOK_SECRET is not configured; skipping signature verification in development mode."
        )

    # 4. Parse JSON payload
    try:
        data: Dict[str, Any] = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # 5. Extract event identifier for deduplication
    event_id = (
        data.get("id")
        or data.get("event_id")
        or request.headers.get("webhook-id")
    )
    event_type = data.get("action") or data.get("event") or data.get("type", "unknown")

    if event_id:
        if is_event_processed(event_id):
            logger.info("Duplicate webhook received and safely ignored: event_id=%s", event_id)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "already_processed", "event_id": event_id},
            )

    # 6. Extract payment and order details
    payload_data = data.get("data", data)
    payment_id = payload_data.get("id") or payload_data.get("payment_id")

    # Extract metadata where our order_id is stored
    metadata = payload_data.get("metadata", {})
    order_id = metadata.get("order_id")

    # Fallback search if metadata structure differs
    if not order_id:
        custom_fields = payload_data.get("custom_fields", {})
        order_id = custom_fields.get("order_id") or payload_data.get("order_id")

    logger.info(
        "Processing Whop Webhook: event_type=%s, order_id=%s, payment_id=%s",
        event_type,
        order_id,
        payment_id,
    )

    if not order_id:
        # If payload doesn't contain an order_id, record and acknowledge
        if event_id:
            record_processed_event(event_id, event_type)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ignored", "reason": "No order_id associated with event"},
        )

    # 7. Process based on event outcome
    # Success events: payment.succeeded, payment_succeeded, checkout.session.completed, etc.
    is_success = any(
        kw in event_type.lower()
        for kw in ("succeed", "paid", "completed", "success")
    )
    is_failure = any(
        kw in event_type.lower()
        for kw in ("failed", "cancelled", "expired", "declined")
    )

    if is_success:
        ok, msg, fulfillment_payload = fulfill_order_and_credit_seller(
            order_id=order_id,
            payment_id=payment_id,
        )
        logger.info("Order fulfillment result for %s: %s (msg: %s)", order_id, ok, msg)

        # Notify buyer and seller in Telegram
        if ok and fulfillment_payload and telegram_app and telegram_app.bot:
            try:
                await notify_user_order_fulfilled(telegram_app.bot, fulfillment_payload)
            except Exception as e:
                logger.error("Failed to notify user via Telegram: %s", e)

    elif is_failure:
        mark_order_failed(order_id=order_id, reason=f"Webhook event: {event_type}")
        logger.info("Order %s marked as failed/cancelled.", order_id)

    # 8. Record event ID to ensure strict idempotency
    if event_id:
        record_processed_event(event_id, event_type)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "success", "order_id": order_id, "event_type": event_type},
    )


if __name__ == "__main__":
    validate_config(strict_bot_token=False)
    logger.info("Starting Web Service on port %s", PORT)
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)
