import logging
from typing import Optional, List

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import is_admin
from database import (
    get_admin_dashboard_stats,
    add_number,
    bulk_add_numbers,
    get_db,
    get_pending_listings,
    get_listing_by_id,
    approve_seller_listing,
    reject_seller_listing,
    get_pending_payouts,
    process_payout_request,
    delete_unsold_number,
    toggle_number_status,
    set_user_ban_status,
    get_system_setting,
    set_system_setting,
    Number,
    User,
    Order,
    Transaction,
    PayoutRequest,
)
from keyboards import (
    get_admin_panel_keyboard,
    get_listing_approval_keyboard,
    get_payout_approval_keyboard,
    get_inventory_item_keyboard,
    get_main_menu_keyboard,
)

logger = logging.getLogger(__name__)

# Conversation states for adding single number
(
    ADD_NUM_NUMBER,
    ADD_NUM_COUNTRY,
    ADD_NUM_SERVICE,
    ADD_NUM_PRICE_INR,
    ADD_NUM_PRICE_USD,
    ADD_NUM_DESC,
) = range(6)

# Conversation states for bulk add
BULK_ADD_INPUT = 10

# Conversation states for commission setting
SET_COMMISSION_INPUT = 20

# Rejection reason conversation state
REJECT_REASON_INPUT = 30


async def check_admin_permission(update: Update) -> bool:
    """Verifies that the caller is registered in ADMIN_IDS."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        if update.callback_query:
            await update.callback_query.answer("❌ Unauthorized: Admin access required.", show_alert=True)
        elif update.message:
            await update.message.reply_text("❌ Unauthorized: You do not have administrator permissions.")
        return False
    return True


# ---------------------------------------------------------
# Admin Dashboard Entry
# ---------------------------------------------------------

async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Opens or refreshes the Admin Dashboard."""
    if not await check_admin_permission(update):
        return

    stats = get_admin_dashboard_stats()
    text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "🛠 **ADMIN CONTROL PANEL**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📊 **System Overview**:\n"
        f"👥 **Total Users**: {stats['total_users']}\n"
        f"📦 **Total Numbers**: {stats['total_numbers']}\n"
        f"  • 🟢 Available: {stats['available_numbers']}\n"
        f"  • 🔴 Sold: {stats['sold_numbers']}\n"
        f"🛒 **Total Orders**: {stats['total_orders']}\n\n"
        "💰 **Financial Metrics**:\n"
        f"• Total Revenue: ₹{stats['revenue_inr']:.2f} | ${stats['revenue_usd']:.2f}\n"
        f"• Seller Earnings: ₹{stats['seller_earnings_inr']:.2f} | ${stats['seller_earnings_usd']:.2f}\n"
        f"• Marketplace Profit: ₹{stats['profit_inr']:.2f} | ${stats['profit_usd']:.2f}\n"
        f"• Commission Rate: {stats['commission_percent']}%\n\n"
        "⏳ **Pending Actions**:\n"
        f"• 📝 Pending Listings: {stats['pending_listings']}\n"
        f"• 💸 Pending Payouts: {stats['pending_payouts']}\n\n"
        "Select an action below:"
    )

    keyboard = get_admin_panel_keyboard()
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ---------------------------------------------------------
# Inventory & Actions
# ---------------------------------------------------------

async def admin_inventory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return

    query = update.callback_query
    await query.answer()

    page = 0
    if query.data and ":" in query.data:
        try:
            page = int(query.data.split(":")[2])
        except Exception:
            page = 0

    page_size = 8
    with get_db() as db:
        numbers = (
            db.query(Number)
            .order_by(Number.id.desc())
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )
        total = db.query(Number).count()

    if not numbers:
        await query.edit_message_text(
            "📦 **Inventory is currently empty.**\nUse ➕ ADD NUMBER or 📥 BULK ADD to add numbers.",
            parse_mode="Markdown",
            reply_markup=get_admin_panel_keyboard(),
        )
        return

    text = f"📦 **Inventory Manager** (Page {page + 1} / {(total + page_size - 1) // page_size})\n\n"
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []

    for num in numbers:
        status_icon = "🟢" if num.status == "available" else ("🟡" if num.status == "reserved" else "🔴")
        text += (
            f"ID #{num.id} | {status_icon} `{num.number}`\n"
            f"   🌍 {num.country} | 📱 {num.service} | 💰 ₹{num.price_inr:.0f} / ${num.price_usd:.2f} | Status: {num.status}\n\n"
        )
        buttons.append([
            InlineKeyboardButton(
                f"Manage #{num.id} ({num.number})",
                callback_data=f"adm_manage_num:{num.id}",
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"adm:inventory:{page - 1}"))
    if (page + 1) * page_size < total:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"adm:inventory:{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="adm:stats")])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def admin_manage_num_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return

    query = update.callback_query
    await query.answer()

    number_id = int(query.data.split(":")[1])
    with get_db() as db:
        num = db.query(Number).filter(Number.id == number_id).first()

    if not num:
        await query.edit_message_text("Number not found.", reply_markup=get_admin_panel_keyboard())
        return

    seller_info = f"Seller User ID: {num.seller_id}" if num.seller_id else "Inventory Origin: Admin"
    text = (
        f"🔍 **Managing Number #{num.id}**\n\n"
        f"• **Number**: `{num.number}`\n"
        f"• **Country**: {num.country}\n"
        f"• **Service**: {num.service}\n"
        f"• **Price INR**: ₹{num.price_inr:.2f}\n"
        f"• **Price USD**: ${num.price_usd:.2f}\n"
        f"• **Status**: `{num.status}`\n"
        f"• **Origin**: {seller_info}\n"
        f"• **Description**: {num.description or 'None'}\n"
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_inventory_item_keyboard(num.id, num.status),
    )


async def admin_toggle_num_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    parts = query.data.split(":")
    number_id = int(parts[1])
    new_status = parts[2]

    ok, msg = toggle_number_status(number_id, new_status)
    await query.answer(msg, show_alert=True)
    await admin_inventory_handler(update, context)


async def admin_delete_num(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    number_id = int(query.data.split(":")[1])

    ok, msg = delete_unsold_number(number_id)
    await query.answer(msg, show_alert=True)
    await admin_inventory_handler(update, context)


# ---------------------------------------------------------
# Pending Listings & Approvals
# ---------------------------------------------------------

async def admin_listings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    await query.answer()

    pending = get_pending_listings()
    if not pending:
        await query.edit_message_text(
            "📝 **No Pending Seller Listings.**\nAll submissions have been reviewed.",
            parse_mode="Markdown",
            reply_markup=get_admin_panel_keyboard(),
        )
        return

    text = f"📝 **Pending Seller Listings ({len(pending)})**:\n\n"
    listing = pending[0]  # Review one by one
    with get_db() as db:
        seller = db.query(User).filter(User.id == listing.seller_id).first()

    seller_name = f"@{seller.username}" if seller and seller.username else (seller.first_name if seller else "Unknown")
    seller_tid = seller.telegram_id if seller else "N/A"

    text += (
        "🆕 **NEW SELLER LISTING REVIEW**\n\n"
        f"👤 **Seller**: {seller_name}\n"
        f"🆔 **Telegram ID**: `{seller_tid}`\n\n"
        f"📱 **Number**: `{listing.number}`\n"
        f"🌍 **Country**: {listing.country}\n"
        f"⚡ **Service**: {listing.service}\n"
        f"💰 **Price INR**: ₹{listing.price_inr:.2f}\n"
        f"💵 **Price USD**: ${listing.price_usd:.2f}\n"
        f"📄 **Description**: {listing.description or 'None'}\n\n"
        f"Total remaining pending: {len(pending)}"
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_listing_approval_keyboard(listing.id),
    )


async def admin_approve_listing_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    listing_id = int(query.data.split(":")[1])

    ok, msg, listing = approve_seller_listing(listing_id)
    if ok and listing:
        await query.answer("✅ Listing Approved and Added to Available Inventory!", show_alert=True)
        # Notify seller
        try:
            with get_db() as db:
                seller = db.query(User).filter(User.id == listing.seller_id).first()
                if seller:
                    await context.bot.send_message(
                        chat_id=seller.telegram_id,
                        text=(
                            f"🎉 **Listing Approved!**\n\n"
                            f"Your virtual number `{listing.number}` ({listing.country} - {listing.service}) "
                            f"has been approved by an administrator and is now live in the marketplace!\n"
                            f"Price: ₹{listing.price_inr:.2f} / ${listing.price_usd:.2f}"
                        ),
                        parse_mode="Markdown",
                    )
        except Exception as e:
            logger.warning("Could not notify seller about listing approval: %s", e)
    else:
        await query.answer(f"Failed: {msg}", show_alert=True)

    await admin_listings_handler(update, context)


async def admin_reject_listing_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    listing_id = int(query.data.split(":")[1])

    ok, msg, listing = reject_seller_listing(listing_id, reason="Does not meet marketplace listing requirements.")
    if ok and listing:
        await query.answer("❌ Listing Rejected.", show_alert=True)
        try:
            with get_db() as db:
                seller = db.query(User).filter(User.id == listing.seller_id).first()
                if seller:
                    await context.bot.send_message(
                        chat_id=seller.telegram_id,
                        text=(
                            f"⚠️ **Listing Rejected**\n\n"
                            f"Your listing for `{listing.number}` was rejected by an administrator.\n"
                            f"Note: {listing.admin_note}"
                        ),
                        parse_mode="Markdown",
                    )
        except Exception as e:
            logger.warning("Could not notify seller about listing rejection: %s", e)
    else:
        await query.answer(f"Failed: {msg}", show_alert=True)

    await admin_listings_handler(update, context)


# ---------------------------------------------------------
# Payout Management
# ---------------------------------------------------------

async def admin_payouts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    await query.answer()

    payouts = get_pending_payouts()
    if not payouts:
        await query.edit_message_text(
            "💰 **No Pending Seller Payout Requests.**\nAll payouts are up to date.",
            parse_mode="Markdown",
            reply_markup=get_admin_panel_keyboard(),
        )
        return

    payout = payouts[0]
    with get_db() as db:
        user = db.query(User).filter(User.id == payout.user_id).first()

    sym = "₹" if payout.currency == "INR" else "$"
    username_str = f"@{user.username}" if user and user.username else "User"

    text = (
        "💸 **PENDING SELLER PAYOUT REQUEST**\n\n"
        f"• **Request ID**: #{payout.id}\n"
        f"• **Seller**: {username_str} (TG ID: `{user.telegram_id if user else 'N/A'}`)\n"
        f"• **Amount**: {sym}{payout.amount:.2f} ({payout.currency})\n"
        f"• **Payout Details**:\n`{payout.payout_details}`\n"
        f"• **Requested At**: {payout.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        f"Remaining pending requests: {len(payouts)}"
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_payout_approval_keyboard(payout.id),
    )


async def admin_payout_action_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    parts = query.data.split(":")
    action_type = parts[0]  # adm_payout_appr, adm_payout_paid, adm_payout_rej
    payout_id = int(parts[1])

    action_map = {
        "adm_payout_appr": "approved",
        "adm_payout_paid": "paid",
        "adm_payout_rej": "rejected",
    }
    action = action_map.get(action_type, "approved")

    ok, msg, payout = process_payout_request(payout_id, action)
    if ok and payout:
        await query.answer(f"Payout #{payout_id} marked as {action}!", show_alert=True)
        # Notify user
        try:
            with get_db() as db:
                user = db.query(User).filter(User.id == payout.user_id).first()
                if user:
                    sym = "₹" if payout.currency == "INR" else "$"
                    status_text = "completed & paid" if action == "paid" else ("approved" if action == "approved" else "rejected and refunded to your wallet")
                    await context.bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            f"🔔 **Payout Request Update**\n\n"
                            f"Your payout request #{payout.id} for {sym}{payout.amount:.2f} has been {status_text}."
                        ),
                        parse_mode="Markdown",
                    )
        except Exception as e:
            logger.warning("Could not notify user of payout update: %s", e)
    else:
        await query.answer(f"Error: {msg}", show_alert=True)

    await admin_payouts_handler(update, context)


# ---------------------------------------------------------
# Users Management
# ---------------------------------------------------------

async def admin_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    await query.answer()

    page = 0
    if ":" in query.data:
        try:
            page = int(query.data.split(":")[2])
        except Exception:
            page = 0

    page_size = 6
    with get_db() as db:
        users = db.query(User).order_by(User.id.desc()).offset(page * page_size).limit(page_size).all()
        total = db.query(User).count()

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    text = f"👥 **User Directory** ({total} Total)\n\n"

    for u in users:
        ban_tag = "🚫 BANNED" if u.is_banned else "Active"
        uname = f"@{u.username}" if u.username else (u.first_name or "N/A")
        text += (
            f"👤 **{uname}** | ID: `{u.telegram_id}`\n"
            f"   Status: {ban_tag} | Currency: {u.currency} | Balance: ₹{u.wallet.balance_inr if u.wallet else 0:.0f} / ${u.wallet.balance_usd if u.wallet else 0:.2f}\n\n"
        )
        toggle_label = "🟢 Unban" if u.is_banned else "🚫 Ban"
        buttons.append([
            InlineKeyboardButton(f"{toggle_label} {uname}", callback_data=f"adm_user_ban:{u.telegram_id}"),
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"adm:users:{page - 1}"))
    if (page + 1) * page_size < total:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"adm:users:{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="adm:stats")])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def admin_toggle_user_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    tid = int(query.data.split(":")[1])

    with get_db() as db:
        u = db.query(User).filter(User.telegram_id == tid).first()
        if not u:
            await query.answer("User not found.", show_alert=True)
            return
        new_ban_state = not u.is_banned
        u.is_banned = new_ban_state
        db.commit()

    state_str = "banned" if new_ban_state else "unbanned"
    await query.answer(f"User `{tid}` has been {state_str}.", show_alert=True)
    await admin_users_handler(update, context)


# ---------------------------------------------------------
# Orders & Payments View
# ---------------------------------------------------------

async def admin_orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    await query.answer()

    with get_db() as db:
        orders = db.query(Order).order_by(Order.id.desc()).limit(8).all()

    if not orders:
        await query.edit_message_text(
            "🛒 **No orders found yet.**",
            parse_mode="Markdown",
            reply_markup=get_admin_panel_keyboard(),
        )
        return

    text = "🛒 **Recent Marketplace Orders**:\n\n"
    for o in orders:
        sym = "₹" if o.currency == "INR" else "$"
        num_str = o.number_item.number if o.number_item else "Unknown"
        text += (
            f"• `{o.order_id}` | Status: **{o.order_status}**\n"
            f"   Item: `{num_str}` | {sym}{o.amount:.2f} {o.currency}\n"
            f"   Date: {o.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        )

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="adm:stats")]
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def admin_payments_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    await query.answer()

    with get_db() as db:
        txs = db.query(Transaction).order_by(Transaction.id.desc()).limit(10).all()

    if not txs:
        await query.edit_message_text(
            "💳 **No transactions recorded yet.**",
            parse_mode="Markdown",
            reply_markup=get_admin_panel_keyboard(),
        )
        return

    text = "💳 **Recent Transactions Ledger**:\n\n"
    for t in txs:
        sym = "₹" if t.currency == "INR" else "$"
        text += (
            f"• [{t.type.upper()}] {sym}{t.amount:.2f} ({t.currency})\n"
            f"   Ref: `{t.reference or 'N/A'}` | {t.created_at.strftime('%m-%d %H:%M')}\n"
            f"   {t.description or ''}\n\n"
        )

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="adm:stats")]
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ---------------------------------------------------------
# Settings (Commission Rate & Configuration)
# ---------------------------------------------------------

async def admin_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    await query.answer()

    comm_val = get_system_setting("commission_percent", "10.0")
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Set 5%", callback_data="adm_set_comm:5.0"),
            InlineKeyboardButton("Set 10%", callback_data="adm_set_comm:10.0"),
            InlineKeyboardButton("Set 15%", callback_data="adm_set_comm:15.0"),
        ],
        [
            InlineKeyboardButton("Set 20%", callback_data="adm_set_comm:20.0"),
            InlineKeyboardButton("Set 25%", callback_data="adm_set_comm:25.0"),
        ],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="adm:stats")],
    ])

    text = (
        "⚙️ **Marketplace Settings**\n\n"
        f"• **Current Marketplace Commission**: `{comm_val}%`\n"
        "• **Supported Currencies**: INR (₹) and USD ($)\n"
        "• **Payment Processor**: Whop Payments (Automated Webhook)\n\n"
        "Choose a new commission percentage below:"
    )

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def admin_set_commission_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_permission(update):
        return
    query = update.callback_query
    rate = query.data.split(":")[1]
    set_system_setting("commission_percent", rate)
    await query.answer(f"Marketplace commission updated to {rate}%!", show_alert=True)
    await admin_settings_handler(update, context)


# ---------------------------------------------------------
# Add Single Number Conversation
# ---------------------------------------------------------

async def add_num_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_admin_permission(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "➕ **Add Authorized Number**\n\n"
        "Step 1/6: Please send the virtual/SMS-testing **Phone Number** (e.g., `+919876543210` or `+12025550143`):",
        parse_mode="Markdown",
    )
    return ADD_NUM_NUMBER


async def add_num_number_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    num_text = update.message.text.strip()
    if len(num_text) < 5:
        await update.message.reply_text("❌ Invalid number format. Please provide a valid number:")
        return ADD_NUM_NUMBER

    context.user_data["new_num_number"] = num_text
    await update.message.reply_text("Step 2/6: Enter the **Country** (e.g., `India`, `United States`, `United Kingdom`):")
    return ADD_NUM_COUNTRY


async def add_num_country_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    country = update.message.text.strip()
    context.user_data["new_num_country"] = country
    await update.message.reply_text("Step 3/6: Enter the **Service / Purpose** (e.g., `SMS Testing`, `WhatsApp Testing`, `API Sandbox`):")
    return ADD_NUM_SERVICE


async def add_num_service_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    svc = update.message.text.strip()
    context.user_data["new_num_service"] = svc
    await update.message.reply_text("Step 4/6: Enter the **Price in INR (₹)** (e.g., `199`):")
    return ADD_NUM_PRICE_INR


async def add_num_price_inr_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        price_inr = float(update.message.text.replace("₹", "").strip())
        if price_inr <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a positive number for INR price:")
        return ADD_NUM_PRICE_INR

    context.user_data["new_num_price_inr"] = price_inr
    await update.message.reply_text("Step 5/6: Enter the **Price in USD ($)** (e.g., `2.50`):")
    return ADD_NUM_PRICE_USD


async def add_num_price_usd_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        price_usd = float(update.message.text.replace("$", "").strip())
        if price_usd <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a positive number for USD price:")
        return ADD_NUM_PRICE_USD

    context.user_data["new_num_price_usd"] = price_usd
    await update.message.reply_text("Step 6/6: Enter a brief **Description / Notes** (or send `/skip`):")
    return ADD_NUM_DESC


async def add_num_desc_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    desc = None if text.startswith("/skip") else text

    data = context.user_data
    num_item = add_number(
        number=data["new_num_number"],
        country=data["new_num_country"],
        service=data["new_num_service"],
        price_inr=data["new_num_price_inr"],
        price_usd=data["new_num_price_usd"],
        description=desc,
        seller_id=None,
    )

    await update.message.reply_text(
        f"✅ **Number Added Successfully!**\n\n"
        f"• **ID**: #{num_item.id}\n"
        f"• **Number**: `{num_item.number}`\n"
        f"• **Country**: {num_item.country}\n"
        f"• **Service**: {num_item.service}\n"
        f"• **Price**: ₹{num_item.price_inr:.2f} / ${num_item.price_usd:.2f}\n"
        f"• **Status**: `available`",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(is_admin_user=True),
    )
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------
# Bulk Add Conversation
# ---------------------------------------------------------

async def bulk_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_admin_permission(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📥 **Bulk Add Numbers**\n\n"
        "Send your inventory rows separated by newlines.\n"
        "Format per row:\n"
        "`number | country | service | price_inr | price_usd`\n\n"
        "Example:\n"
        "`+919876543210 | India | SMS Testing | 199 | 2.50`\n"
        "`+12025550143 | United States | API Testing | 249 | 3.00`\n\n"
        "Send `/cancel` to abort.",
        parse_mode="Markdown",
    )
    return BULK_ADD_INPUT


async def bulk_add_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text.startswith("/cancel"):
        await update.message.reply_text("Bulk addition cancelled.", reply_markup=get_main_menu_keyboard(True))
        return ConversationHandler.END

    lines = text.splitlines()
    added, failed, errors = bulk_add_numbers(lines)

    summary = (
        f"📥 **Bulk Add Results**:\n\n"
        f"✅ **Added**: {added}\n"
        f"❌ **Failed**: {failed}\n"
    )
    if errors:
        summary += "\n**Errors Encountered**:\n"
        for err in errors[:10]:
            summary += f"• {err}\n"
        if len(errors) > 10:
            summary += f"...and {len(errors) - 10} more.\n"

    await update.message.reply_text(
        summary,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(is_admin_user=True),
    )
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Action cancelled.", reply_markup=get_main_menu_keyboard(True))
    return ConversationHandler.END
