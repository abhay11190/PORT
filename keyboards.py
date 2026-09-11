from typing import List, Tuple, Optional
from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from models import Number, Listing, Order, PayoutRequest


def get_main_menu_keyboard(is_admin_user: bool = False) -> ReplyKeyboardMarkup:
    """Returns the main menu ReplyKeyboardMarkup matching the requested layout."""
    keyboard = [
        [KeyboardButton("🛒 BUY NUMBER"), KeyboardButton("💰 SELL NUMBER")],
        [KeyboardButton("📦 MY ORDERS"), KeyboardButton("📋 MY LISTINGS")],
        [KeyboardButton("💳 WALLET"), KeyboardButton("💵 EARNINGS")],
        [KeyboardButton("💱 CURRENCY"), KeyboardButton("👤 PROFILE")],
        [KeyboardButton("📊 STATISTICS"), KeyboardButton("❓ SUPPORT")],
    ]
    if is_admin_user:
        keyboard.append([KeyboardButton("🛠 ADMIN PANEL")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )


# ---------------------------------------------------------
# Buy Flow Inline Keyboards
# ---------------------------------------------------------

def get_countries_keyboard(countries: List[Tuple[str, int]]) -> InlineKeyboardMarkup:
    """List of country buttons with counts."""
    buttons = []
    # Display 2 per row
    row = []
    for country, count in countries:
        row.append(
            InlineKeyboardButton(
                text=f"{country} ({count})",
                callback_data=f"buy_country:{country}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_menu")])
    return InlineKeyboardMarkup(buttons)


def get_services_keyboard(country: str, services: List[Tuple[str, int]]) -> InlineKeyboardMarkup:
    """List of services available for selected country."""
    buttons = []
    row = []
    for service, count in services:
        row.append(
            InlineKeyboardButton(
                text=f"{service} ({count})",
                callback_data=f"buy_svc:{country}:{service}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("🔙 Back to Countries", callback_data="buy_back_countries"),
        InlineKeyboardButton("❌ Close", callback_data="close_menu"),
    ])
    return InlineKeyboardMarkup(buttons)


def get_number_buy_keyboard(number_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🛒 BUY NOW (ID: #{number_id})", callback_data=f"buy_num:{number_id}")],
    ])


def get_purchase_confirm_keyboard(number_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 PAY NOW", callback_data=f"pay_confirm:{number_id}")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="pay_cancel")],
    ])


def get_checkout_keyboard(checkout_url: str, order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay via Whop Checkout", url=checkout_url)],
        [InlineKeyboardButton("❌ Cancel Order", callback_data=f"order_cancel:{order_id}")],
    ])


# ---------------------------------------------------------
# Currency Selection
# ---------------------------------------------------------

def get_currency_keyboard(current_currency: str) -> InlineKeyboardMarkup:
    inr_label = "✅ 🇮🇳 INR (₹)" if current_currency == "INR" else "🇮🇳 INR (₹)"
    usd_label = "✅ 🇺🇸 USD ($)" if current_currency == "USD" else "🇺🇸 USD ($)"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(inr_label, callback_data="set_curr:INR"),
            InlineKeyboardButton(usd_label, callback_data="set_curr:USD"),
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
    ])


# ---------------------------------------------------------
# Payout Keyboards
# ---------------------------------------------------------

def get_payout_currency_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇮🇳 Withdraw INR (₹)", callback_data="payout_curr:INR"),
            InlineKeyboardButton("🇺🇸 Withdraw USD ($)", callback_data="payout_curr:USD"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="close_menu")],
    ])


# ---------------------------------------------------------
# Admin Keyboards
# ---------------------------------------------------------

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ ADD NUMBER", callback_data="adm:add_num"),
            InlineKeyboardButton("📥 BULK ADD", callback_data="adm:bulk_add"),
        ],
        [
            InlineKeyboardButton("📦 INVENTORY", callback_data="adm:inventory:0"),
            InlineKeyboardButton("📝 PENDING LISTINGS", callback_data="adm:listings"),
        ],
        [
            InlineKeyboardButton("👥 USERS", callback_data="adm:users:0"),
            InlineKeyboardButton("🛒 ORDERS", callback_data="adm:orders:0"),
        ],
        [
            InlineKeyboardButton("💳 PAYMENTS", callback_data="adm:payments:0"),
            InlineKeyboardButton("💰 SELLER PAYOUTS", callback_data="adm:payouts"),
        ],
        [
            InlineKeyboardButton("📊 STATISTICS", callback_data="adm:stats"),
            InlineKeyboardButton("⚙️ SETTINGS", callback_data="adm:settings"),
        ],
        [
            InlineKeyboardButton("🔙 Back to Main Menu", callback_data="adm:close"),
        ],
    ])


def get_listing_approval_keyboard(listing_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"adm_appr_list:{listing_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"adm_rej_list:{listing_id}"),
        ],
    ])


def get_payout_approval_keyboard(payout_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"adm_payout_appr:{payout_id}"),
            InlineKeyboardButton("📝 MARK PAID", callback_data=f"adm_payout_paid:{payout_id}"),
        ],
        [
            InlineKeyboardButton("❌ REJECT & REFUND", callback_data=f"adm_payout_rej:{payout_id}"),
        ],
    ])


def get_inventory_item_keyboard(number_id: int, current_status: str) -> InlineKeyboardMarkup:
    toggle_btn = (
        InlineKeyboardButton("🔴 Disable", callback_data=f"adm_num_toggle:{number_id}:inactive")
        if current_status == "available"
        else InlineKeyboardButton("🟢 Enable", callback_data=f"adm_num_toggle:{number_id}:available")
    )
    return InlineKeyboardMarkup([
        [toggle_btn],
        [InlineKeyboardButton("🗑 Delete Number", callback_data=f"adm_num_del:{number_id}")],
        [InlineKeyboardButton("🔙 Back to Inventory", callback_data="adm:inventory:0")],
    ])
