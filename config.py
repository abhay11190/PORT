import os
import sys
from typing import Set
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    sys.stderr.write(
        "\n[FATAL ERROR] BOT_TOKEN is missing or empty! "
        "Please provide a valid Telegram bot token via the BOT_TOKEN environment variable.\n\n"
    )
    # Provide a non-crashing fallback for preview/linting environments if needed, but raise ValueError when running
    # To satisfy "The bot must fail with a clear error message if BOT_TOKEN is missing"
    if os.getenv("STRICT_ENV_CHECK", "true").lower() in ("true", "1", "yes") and "pytest" not in sys.modules:
        # If running as production app, we enforce this check in app startup, but we will store empty or raise
        pass

ADMIN_IDS_RAW: str = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS: Set[int] = set()
if ADMIN_IDS_RAW:
    for part in ADMIN_IDS_RAW.split(","):
        part = part.strip()
        if part.isdigit():
            ADMIN_IDS.add(int(part))

WHOP_API_KEY: str = os.getenv("WHOP_API_KEY", "").strip()
WHOP_WEBHOOK_SECRET: str = os.getenv("WHOP_WEBHOOK_SECRET", "").strip()
# WHOP_COMPANY_ID: Whop's internal identifier (biz_...) assigned to every creator / store,
# including individual accounts verified with PAN card / personal ID.
# Can be left blank in .env if WHOP_API_KEY is provided (auto-resolved via Whop API).
WHOP_COMPANY_ID: str = os.getenv("WHOP_COMPANY_ID", "").strip()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///marketplace.db").strip()
PORT: int = int(os.getenv("PORT", "10000").strip() or "10000")
SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@")

# Default marketplace commission percentage (e.g., 10%)
DEFAULT_COMMISSION_PERCENT: float = 10.0


def is_admin(telegram_id: int) -> bool:
    """Check whether a given Telegram user ID has administrator privileges."""
    return telegram_id in ADMIN_IDS


def validate_config(strict_bot_token: bool = True) -> None:
    """
    Validates configuration at startup.
    Produces clear, actionable error messages for any missing required credentials.
    """
    errors = []

    if strict_bot_token and not BOT_TOKEN:
        errors.append(
            "❌ [CRITICAL] BOT_TOKEN is missing!\n"
            "   -> Please get your Telegram Bot token from @BotFather and set BOT_TOKEN."
        )

    if not WHOP_API_KEY:
        errors.append(
            "❌ [STARTUP ERROR] WHOP_API_KEY is missing!\n"
            "   -> Required for payment checkout sessions and auto-discovering your store's biz_... ID.\n"
            "   -> Obtain it from: Whop Dashboard > Settings > Developer > API Keys (e.g. whop_live_...)"
        )

    if not WHOP_WEBHOOK_SECRET:
        errors.append(
            "❌ [STARTUP ERROR] WHOP_WEBHOOK_SECRET is missing!\n"
            "   -> Required for cryptographic HMAC signature verification of incoming payment events.\n"
            "   -> Obtain it from: Whop Dashboard > Settings > Developer > Webhooks (e.g. whsec_...)"
        )

    if errors:
        border = "=" * 76
        err_msg = (
            f"\n{border}\n"
            f"⚠️  VIRTUAL NUMBER MARKETPLACE CONFIGURATION WARNING / ERROR(S):\n"
            f"{border}\n"
            + "\n\n".join(errors)
            + f"\n{border}\n"
            + "ℹ️  Note: WHOP_COMPANY_ID is optional and auto-discovered. No business tax ID needed.\n"
            + f"{border}\n"
        )
        sys.stderr.write(err_msg)
        sys.stderr.flush()

    if strict_bot_token and not BOT_TOKEN:
        raise ValueError(
            "CRITICAL: BOT_TOKEN is not configured! "
            "Set BOT_TOKEN in your environment variables before starting the bot."
        )

