import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import is_admin, SUPPORT_USERNAME, ADMIN_IDS
from database import (
    get_or_create_user,
    get_user_by_telegram_id,
    set_user_currency,
    get_available_countries,
    get_available_services,
    get_available_numbers_by_service,
    get_number_by_id,
    create_pending_purchase_order,
    cancel_pending_order,
    create_seller_listing,
    create_payout_request,
    get_user_stats,
    get_db,
    User,
    Order,
    Listing,
    Transaction,
    Wallet,
)
from keyboards import (
    get_main_menu_keyboard,
    get_countries_keyboard,
    get_services_keyboard,
    get_number_buy_keyboard,
    get_purchase_confirm_keyboard,
    get_checkout_keyboard,
    get_currency_keyboard,
    get_payout_currency_keyboard,
    get_listing_approval_keyboard,
)
from payments import payment_provider

logger = logging.getLogger(__name__)

# Sell number conversation states
(
    SELL_NUM,
    SELL_COUNTRY,
    SELL_SERVICE,
    SELL_PRICE_INR,
    SELL_PRICE_USD,
    SELL_DESC,
    SELL_CONFIRM,
) = range(7)

# Payout conversation states
(
    PAYOUT_CURRENCY_STATE,
    PAYOUT_AMOUNT_STATE,
    PAYOUT_DETAILS_STATE,
) = range(10, 13)


# ---------------------------------------------------------
# /start & Main Menu
# ---------------------------------------------------------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    if not tg_user:
        return

    user = get_or_create_user(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
    )

    if user.is_banned:
        await update.message.reply_text("❌ Your account is currently suspended. Please contact support.")
        return

    admin_status = is_admin(tg_user.id)
    text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "💎 **PREMIUM MARKETPLACE**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Welcome to **Premium Virtual Number Marketplace**!\n\n"
        "**Features**:\n"
        "• 🛒 Buy authorized virtual numbers\n"
        "• 💰 Sell your authorized inventory\n"
        "• ⚡ Fast payment verification via Whop\n"
        "• 📦 Secure order tracking & instant delivery\n"
        "• 💱 Dual currency pricing (INR / USD)\n"
        "• 💵 Guaranteed seller earnings & payouts\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Please select an option from the menu below:"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(is_admin_user=admin_status),
    )


# ---------------------------------------------------------
# ReplyKeyboardMarkup Menu Handlers
# ---------------------------------------------------------

async def menu_buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if user and user.is_banned:
        await update.message.reply_text("❌ Your account is suspended.")
        return

    countries = get_available_countries()
    if not countries:
        await update.message.reply_text(
            "🛒 **No Numbers Available**\n\n"
            "There are currently no active virtual numbers in stock.\n"
            "Please check back shortly or list your own inventory!",
            parse_mode="Markdown",
        )
        return

    text = (
        "🛒 **Virtual Number Catalog**\n\n"
        "🌍 **Select Country**:\n"
        "Choose a country to view available authorized numbers."
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_countries_keyboard(countries),
    )


async def menu_my_orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user:
        return

    with get_db() as db:
        orders = (
            db.query(Order)
            .filter(Order.user_id == user.id)
            .order_by(Order.id.desc())
            .limit(10)
            .all()
        )

    if not orders:
        await update.message.reply_text(
            "📦 **My Orders**\n\nYou have not placed any orders yet.",
            parse_mode="Markdown",
        )
        return

    text = "📦 **Your Order History**:\n\n"
    for o in orders:
        sym = "₹" if o.currency == "INR" else "$"
        num_str = o.number_item.number if o.number_item else "N/A"
        cntry = o.number_item.country if o.number_item else "Unknown"
        svc = o.number_item.service if o.number_item else "Unknown"
        status_emoji = "✅" if o.order_status == "fulfilled" else ("⏳" if o.order_status == "pending" else "❌")

        text += (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **Order**: `{o.order_id}`\n"
            f"📱 **Number**: `{num_str}`\n"
            f"🌍 **Country**: {cntry} | {svc}\n"
            f"💰 **Price**: {sym}{o.amount:.2f} {o.currency}\n"
            f"💳 **Payment**: `{o.payment_status}`\n"
            f"{status_emoji} **Status**: `{o.order_status}`\n"
            f"📅 **Date**: {o.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        )
    text += "━━━━━━━━━━━━━━━━━━"

    await update.message.reply_text(text, parse_mode="Markdown")


async def menu_my_listings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user:
        return

    with get_db() as db:
        listings = (
            db.query(Listing)
            .filter(Listing.seller_id == user.id)
            .order_by(Listing.id.desc())
            .limit(10)
            .all()
        )

    if not listings:
        await update.message.reply_text(
            "📋 **My Listings**\n\n"
            "You haven't listed any numbers yet.\n"
            "Use **💰 SELL NUMBER** to submit your authorized inventory.",
            parse_mode="Markdown",
        )
        return

    text = "📋 **Your Submitted Listings**:\n\n"
    for l in listings:
        status_icons = {
            "pending": "⏳ Pending Approval",
            "approved": "🟢 Live in Marketplace",
            "rejected": "❌ Rejected",
            "sold": "🎉 Sold",
            "cancelled": "🚫 Cancelled",
        }
        badge = status_icons.get(l.status, l.status)
        text += (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📱 `{l.number}` ({l.country} - {l.service})\n"
            f"💰 ₹{l.price_inr:.0f} / ${l.price_usd:.2f}\n"
            f"🏷 **Status**: {badge}\n"
        )
        if l.admin_note:
            text += f"📝 **Admin Note**: {l.admin_note}\n"
        text += f"📅 {l.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    text += "━━━━━━━━━━━━━━━━━━"

    await update.message.reply_text(text, parse_mode="Markdown")


async def menu_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user or not user.wallet:
        return

    with get_db() as db:
        txs = (
            db.query(Transaction)
            .filter(Transaction.user_id == user.id)
            .order_by(Transaction.id.desc())
            .limit(5)
            .all()
        )

    stats = get_user_stats(user.id)

    text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "💳 **ACCOUNT WALLET**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "💰 **Withdrawable Balances**:\n"
        f"🇮🇳 **INR Balance**: ₹{user.wallet.balance_inr:.2f}\n"
        f"🇺🇸 **USD Balance**: ${user.wallet.balance_usd:.2f}\n\n"
        "📈 **Financial Summary**:\n"
        f"• 💵 Total Earned: ₹{stats['earned_inr']:.2f} | ${stats['earned_usd']:.2f}\n"
        f"• 🛒 Total Spent: ₹{stats['spent_inr']:.2f} | ${stats['spent_usd']:.2f}\n\n"
        "📊 **Recent Transactions**:\n"
    )

    if not txs:
        text += "No transactions recorded yet.\n"
    else:
        for t in txs:
            sym = "₹" if t.currency == "INR" else "$"
            text += f"• [{t.type.upper()}] {sym}{t.amount:.2f} - {t.description or t.reference}\n"

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 REQUEST PAYOUT", callback_data="start_payout_req")],
    ])

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def menu_earnings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user or not user.wallet:
        return

    stats = get_user_stats(user.id)
    text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "💵 **SELLER EARNINGS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🎉 **Sales Statistics**:\n"
        f"• Total Numbers Sold: {stats['sales']}\n"
        f"• Active / Submitted Listings: {stats['listings']}\n\n"
        "💰 **Earnings Breakdown**:\n"
        f"• Lifetime INR Earnings: ₹{stats['earned_inr']:.2f}\n"
        f"• Lifetime USD Earnings: ${stats['earned_usd']:.2f}\n\n"
        "🏦 **Available for Payout**:\n"
        f"• ₹{user.wallet.balance_inr:.2f} INR\n"
        f"• ${user.wallet.balance_usd:.2f} USD\n\n"
        "Seller payouts are processed safely by administrators upon request."
    )

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 REQUEST PAYOUT", callback_data="start_payout_req")],
    ])

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def menu_currency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    curr = user.currency if user else "INR"

    text = (
        "💱 **Currency Preference**\n\n"
        f"Current Selected Currency: **{curr}**\n\n"
        "Choose your preferred currency for browsing and purchasing numbers:"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_currency_keyboard(curr),
    )


async def set_currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    new_curr = query.data.split(":")[1]
    set_user_currency(update.effective_user.id, new_curr)

    await query.edit_message_text(
        f"✅ Preferred currency updated to **{new_curr}**!",
        parse_mode="Markdown",
        reply_markup=get_currency_keyboard(new_curr),
    )


async def menu_profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user:
        return

    text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "👤 **USER PROFILE**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"• **Telegram ID**: `{user.telegram_id}`\n"
        f"• **Username**: @{user.username if user.username else 'N/A'}\n"
        f"• **Name**: {user.first_name or 'Anonymous'}\n"
        f"• **Preferred Currency**: {user.currency}\n"
        f"• **Status**: {'🚫 Suspended' if user.is_banned else '🟢 Active'}\n"
        f"• **Member Since**: {user.created_at.strftime('%Y-%m-%d')}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def menu_statistics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user:
        return

    stats = get_user_stats(user.id)
    text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "📊 **YOUR ACCOUNT STATISTICS**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🛒 **Total Orders**: {stats['orders']}\n"
        f"✅ **Completed Purchases**: {stats['purchases']}\n"
        f"💵 **Total Spent**: ₹{stats['spent_inr']:.2f} / ${stats['spent_usd']:.2f}\n\n"
        f"📋 **Listings Created**: {stats['listings']}\n"
        f"🎉 **Numbers Sold**: {stats['sales']}\n"
        f"💰 **Total Earned**: ₹{stats['earned_inr']:.2f} / ${stats['earned_usd']:.2f}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def menu_support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if SUPPORT_USERNAME:
        text = (
            "❓ **Customer Support**\n\n"
            f"Need assistance with numbers, orders, or seller listings?\n\n"
            f"👉 Contact our support team: @{SUPPORT_USERNAME}\n\n"
            "Available 24/7 for customer queries."
        )
    else:
        text = (
            "❓ **Customer Support**\n\n"
            "Please contact the administrator for any questions or support requests."
        )
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------
# Interactive Buy Flow Callbacks
# ---------------------------------------------------------

async def buy_country_selected_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    country = query.data.split(":", 1)[1]
    services = get_available_services(country)

    if not services:
        await query.edit_message_text(
            f"No services currently available for {country}.",
            reply_markup=get_countries_keyboard(get_available_countries()),
        )
        return

    text = (
        f"🛒 **Country**: {country}\n\n"
        "📱 **Select Service / Purpose**:\n"
        "Choose an SMS-testing or virtual service category:"
    )
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_services_keyboard(country, services),
    )


async def buy_back_countries_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    countries = get_available_countries()
    await query.edit_message_text(
        "🌍 **Select Country**:\nChoose a country to view available authorized numbers.",
        parse_mode="Markdown",
        reply_markup=get_countries_keyboard(countries),
    )


async def buy_service_selected_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    country = parts[1]
    service = parts[2]

    numbers = get_available_numbers_by_service(country, service)
    if not numbers:
        await query.edit_message_text(
            f"No available numbers for {country} ({service}) right now.",
            reply_markup=get_countries_keyboard(get_available_countries()),
        )
        return

    user = get_user_by_telegram_id(update.effective_user.id)
    user_curr = user.currency if user else "INR"

    await query.edit_message_text(
        f"📱 **Available Numbers for {country} ({service})**:\nSelect a number to purchase:",
        parse_mode="Markdown",
    )

    for num in numbers:
        price_display = f"₹{num.price_inr:.0f}" if user_curr == "INR" else f"${num.price_usd:.2f}"
        both_prices = f"₹{num.price_inr:.0f} / ${num.price_usd:.2f}"

        desc_line = f"• *Notes*: {num.description}\n" if num.description else ""
        num_card = (
            "━━━━━━━━━━━━━━━━━━\n"
            f"🌍 **Country**: {num.country}\n"
            f"📱 **Service**: {num.service}\n"
            f"💰 **Price**: {price_display} ({both_prices})\n"
            f"🆔 **Number ID**: `#{num.id}`\n"
            f"{desc_line}"
            "━━━━━━━━━━━━━━━━━━"
        )
        await query.message.reply_text(
            num_card,
            parse_mode="Markdown",
            reply_markup=get_number_buy_keyboard(num.id),
        )


async def buy_number_selected_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    number_id = int(query.data.split(":")[1])
    num = get_number_by_id(number_id)

    if not num or num.status != "available":
        await query.edit_message_text(
            "❌ This number is no longer available.",
            reply_markup=None,
        )
        return

    user = get_user_by_telegram_id(update.effective_user.id)
    user_curr = user.currency if user else "INR"
    price = f"₹{num.price_inr:.2f}" if user_curr == "INR" else f"${num.price_usd:.2f}"

    text = (
        "🛒 **Confirm Purchase**\n\n"
        f"• **Number ID**: `#{num.id}`\n"
        f"• **Country**: {num.country}\n"
        f"• **Service**: {num.service}\n"
        f"• **Price**: **{price} {user_curr}**\n\n"
        "Click **💳 PAY NOW** to proceed to secure Whop Checkout."
    )
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_purchase_confirm_keyboard(num.id),
    )


async def pay_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user:
        return
    if user.is_banned:
        await query.edit_message_text("❌ Account suspended.")
        return

    number_id = int(query.data.split(":")[1])
    order, msg = create_pending_purchase_order(user.id, number_id, user.currency)
    if not order:
        await query.edit_message_text(f"❌ Failed to reserve number: {msg}")
        return

    num = get_number_by_id(number_id)
    desc = f"{num.country} {num.service} Virtual Number" if num else "Virtual Number"

    # Create Whop checkout session
    payment_res = await payment_provider.create_checkout_session(
        order_id=order.order_id,
        amount=order.amount,
        currency=order.currency,
        description=desc,
        user_id=user.id,
    )

    sym = "₹" if order.currency == "INR" else "$"
    checkout_text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "💳 **WHOP PAYMENT CHECKOUT**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 **Order ID**: `{order.order_id}`\n"
        f"💰 **Amount**: **{sym}{order.amount:.2f} {order.currency}**\n"
        f"📱 **Item**: `#{number_id}` ({desc})\n\n"
        "Click the button below to complete your payment on Whop.\n"
        "Your order will be **automatically verified and delivered** right here once payment is confirmed!"
    )

    await query.edit_message_text(
        checkout_text,
        parse_mode="Markdown",
        reply_markup=get_checkout_keyboard(payment_res.checkout_url, order.order_id),
    )


async def order_cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    order_id = query.data.split(":")[1]
    ok, msg = cancel_pending_order(order_id)
    if ok:
        await query.edit_message_text(f"❌ Order `{order_id}` has been cancelled and the number was returned to available stock.")
    else:
        await query.edit_message_text(f"Could not cancel order: {msg}")


async def pay_cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Purchase cancelled.")
    await query.edit_message_text("❌ Purchase cancelled.")


async def close_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        await query.edit_message_text("Closed.")


# ---------------------------------------------------------
# Seller Listing Conversation Flow
# ---------------------------------------------------------

async def sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if user and user.is_banned:
        await update.message.reply_text("❌ Your account is suspended.")
        return ConversationHandler.END

    text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 **SELL VIRTUAL / SMS-TESTING NUMBER**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "List your authorized virtual number for sale on our marketplace.\n"
        "Your listing will be reviewed by administrators before going live.\n\n"
        "Step 1/6: Send the **Phone Number** (e.g. `+12025550199`):\n"
        "(Send `/cancel` at any time to abort)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
    return SELL_NUM


async def sell_num_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if len(text) < 5:
        await update.message.reply_text("❌ Invalid number format. Please send a valid phone number:")
        return SELL_NUM

    context.user_data["sell_number"] = text
    await update.message.reply_text("Step 2/6: Enter the **Country** (e.g., `United States`, `India`, `United Kingdom`):")
    return SELL_COUNTRY


async def sell_country_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["sell_country"] = update.message.text.strip()
    await update.message.reply_text("Step 3/6: Enter the **Service / Purpose** (e.g., `SMS Testing`, `API Verification`):")
    return SELL_SERVICE


async def sell_service_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["sell_service"] = update.message.text.strip()
    await update.message.reply_text("Step 4/6: Enter your selling price in **INR (₹)** (e.g., `199`):")
    return SELL_PRICE_INR


async def sell_price_inr_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        p_inr = float(update.message.text.replace("₹", "").strip())
        if p_inr <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a positive number for INR price:")
        return SELL_PRICE_INR

    context.user_data["sell_price_inr"] = p_inr
    await update.message.reply_text("Step 5/6: Enter your selling price in **USD ($)** (e.g., `2.50`):")
    return SELL_PRICE_USD


async def sell_price_usd_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        p_usd = float(update.message.text.replace("$", "").strip())
        if p_usd <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a positive number for USD price:")
        return SELL_PRICE_USD

    context.user_data["sell_price_usd"] = p_usd
    await update.message.reply_text("Step 6/6: Enter a brief **Description or notes** for buyers (or send `/skip`):")
    return SELL_DESC


async def sell_desc_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    desc = None if text.startswith("/skip") else text

    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user:
        await update.message.reply_text("User error.")
        return ConversationHandler.END

    d = context.user_data
    listing = create_seller_listing(
        seller_id=user.id,
        number=d["sell_number"],
        country=d["sell_country"],
        service=d["sell_service"],
        price_inr=d["sell_price_inr"],
        price_usd=d["sell_price_usd"],
        description=desc,
    )

    await update.message.reply_text(
        "✅ **Listing Submitted for Review!**\n\n"
        f"• **Listing ID**: #{listing.id}\n"
        f"• **Number**: `{listing.number}`\n"
        f"• **Country**: {listing.country}\n"
        f"• **Service**: {listing.service}\n"
        f"• **Price**: ₹{listing.price_inr:.2f} / ${listing.price_usd:.2f}\n"
        f"• **Status**: `⏳ Pending Admin Approval`\n\n"
        "You will be notified once an administrator approves your listing.",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(is_admin(tg_user.id)),
    )

    # Notify all admins immediately
    admin_notif = (
        "🆕 **NEW SELLER LISTING SUBMITTED**\n\n"
        f"👤 **Seller**: @{tg_user.username or 'N/A'}\n"
        f"🆔 **Telegram ID**: `{tg_user.id}`\n\n"
        f"📱 **Number**: `{listing.number}`\n"
        f"🌍 **Country**: {listing.country}\n"
        f"⚡ **Service**: {listing.service}\n"
        f"💰 **Price INR**: ₹{listing.price_inr:.2f}\n"
        f"💵 **Price USD**: ${listing.price_usd:.2f}\n"
        f"📄 **Description**: {listing.description or 'None'}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_notif,
                parse_mode="Markdown",
                reply_markup=get_listing_approval_keyboard(listing.id),
            )
        except Exception as e:
            logger.warning("Failed to notify admin %s: %s", admin_id, e)

    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------
# Payout Request Conversation Flow
# ---------------------------------------------------------

async def payout_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user or not user.wallet:
        await query.edit_message_text("Wallet not found.")
        return ConversationHandler.END

    if user.wallet.balance_inr <= 0 and user.wallet.balance_usd <= 0:
        await query.edit_message_text(
            "❌ You do not have any withdrawable balance right now.",
            reply_markup=None,
        )
        return ConversationHandler.END

    text = (
        "💸 **Request Seller Payout**\n\n"
        f"Available: ₹{user.wallet.balance_inr:.2f} INR | ${user.wallet.balance_usd:.2f} USD\n\n"
        "Select the currency you wish to withdraw:"
    )
    await query.edit_message_text(text, reply_markup=get_payout_currency_keyboard())
    return PAYOUT_CURRENCY_STATE


async def payout_currency_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    curr = query.data.split(":")[1]
    context.user_data["payout_curr"] = curr

    sym = "₹" if curr == "INR" else "$"
    await query.edit_message_text(
        f"Step 2/3: Enter the amount you wish to withdraw in **{curr}** ({sym}):\n"
        "(Send `/cancel` to abort)"
    )
    return PAYOUT_AMOUNT_STATE


async def payout_amount_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text.replace("₹", "").replace("$", "").strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid positive payout amount:")
        return PAYOUT_AMOUNT_STATE

    context.user_data["payout_amount"] = amount
    await update.message.reply_text(
        "Step 3/3: Please enter your **Payout Details**\n"
        "(e.g., UPI ID, Bank Transfer account & IFSC, or PayPal address):"
    )
    return PAYOUT_DETAILS_STATE


async def payout_details_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    details = update.message.text.strip()
    tg_user = update.effective_user
    user = get_user_by_telegram_id(tg_user.id)
    if not user:
        return ConversationHandler.END

    d = context.user_data
    ok, msg, payout = create_payout_request(
        user_id=user.id,
        amount=d["payout_amount"],
        currency=d["payout_curr"],
        payout_details=details,
    )

    if not ok:
        await update.message.reply_text(f"❌ Payout Request Failed: {msg}")
        return ConversationHandler.END

    sym = "₹" if payout.currency == "INR" else "$"
    await update.message.reply_text(
        f"✅ **Payout Request Submitted!**\n\n"
        f"• **Request ID**: #{payout.id}\n"
        f"• **Amount**: {sym}{payout.amount:.2f} {payout.currency}\n"
        f"• **Destination**: `{details}`\n"
        f"• **Status**: `⏳ Pending Admin Verification`\n\n"
        "An administrator will process your payout and you will receive a confirmation message.",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(is_admin(tg_user.id)),
    )

    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            from keyboards import get_payout_approval_keyboard
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💸 **NEW PAYOUT REQUEST #{payout.id}**\n\n"
                    f"Seller: @{tg_user.username or 'N/A'} (ID: `{tg_user.id}`)\n"
                    f"Amount: {sym}{payout.amount:.2f} {payout.currency}\n"
                    f"Details: `{details}`"
                ),
                parse_mode="Markdown",
                reply_markup=get_payout_approval_keyboard(payout.id),
            )
        except Exception as e:
            logger.warning("Could not notify admin %s of payout request: %s", admin_id, e)

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_sell_or_payout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Operation cancelled.", reply_markup=get_main_menu_keyboard(is_admin(update.effective_user.id)))
    return ConversationHandler.END
