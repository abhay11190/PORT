import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN, is_admin
import handlers
import admin

logger = logging.getLogger(__name__)

bot_app: Optional[Application] = None


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global error handler for all unhandled exceptions in the Telegram bot.
    Ensures the bot never crashes and secrets are never leaked into logs.
    """
    error = context.error
    err_str = str(error)

    # Sanitize common secret values if they appear in tracebacks
    for secret in (BOT_TOKEN,):
        if secret and secret in err_str:
            err_str = err_str.replace(secret, "[REDACTED_SECRET]")

    logger.error("Exception while handling update: %s", err_str, exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An unexpected temporary issue occurred while processing your request. "
                "Please try again in a moment."
            )
        except Exception:
            pass


def build_telegram_application() -> Application:
    """Builds and wires up the Telegram Application with all handlers and conversation states."""
    global bot_app

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing! Please set the BOT_TOKEN environment variable.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # 1. Error Handler
    app.add_error_handler(global_error_handler)

    # 2. Seller Listing Conversation
    sell_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^💰 SELL NUMBER$"), handlers.sell_start),
            CommandHandler("sell", handlers.sell_start),
        ],
        states={
            handlers.SELL_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.sell_num_step)],
            handlers.SELL_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.sell_country_step)],
            handlers.SELL_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.sell_service_step)],
            handlers.SELL_PRICE_INR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.sell_price_inr_step)],
            handlers.SELL_PRICE_USD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.sell_price_usd_step)],
            handlers.SELL_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.sell_desc_step),
                CommandHandler("skip", handlers.sell_desc_step),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel_sell_or_payout),
            MessageHandler(filters.Regex("^(❌ Cancel|/cancel)$"), handlers.cancel_sell_or_payout),
        ],
    )
    app.add_handler(sell_conv)

    # 3. Payout Request Conversation
    payout_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handlers.payout_start_cb, pattern="^start_payout_req$"),
        ],
        states={
            handlers.PAYOUT_CURRENCY_STATE: [CallbackQueryHandler(handlers.payout_currency_chosen, pattern="^payout_curr:")],
            handlers.PAYOUT_AMOUNT_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.payout_amount_step)],
            handlers.PAYOUT_DETAILS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.payout_details_step)],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel_sell_or_payout),
            CallbackQueryHandler(handlers.close_menu_cb, pattern="^close_menu$"),
        ],
        per_chat=True,
        per_user=True,
        per_message=False,
    )
    app.add_handler(payout_conv)

    # 4. Admin Add Number Conversation
    admin_add_num_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin.add_num_start, pattern="^adm:add_num$"),
        ],
        states={
            admin.ADD_NUM_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_num_number_step)],
            admin.ADD_NUM_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_num_country_step)],
            admin.ADD_NUM_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_num_service_step)],
            admin.ADD_NUM_PRICE_INR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_num_price_inr_step)],
            admin.ADD_NUM_PRICE_USD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_num_price_usd_step)],
            admin.ADD_NUM_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_num_desc_step),
                CommandHandler("skip", admin.add_num_desc_step),
            ],
        },
        fallbacks=[CommandHandler("cancel", admin.cancel_conversation)],
        per_chat=True,
        per_user=True,
        per_message=False,
    )
    app.add_handler(admin_add_num_conv)

    # 5. Admin Bulk Add Conversation
    admin_bulk_add_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin.bulk_add_start, pattern="^adm:bulk_add$"),
        ],
        states={
            admin.BULK_ADD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.bulk_add_process)],
        },
        fallbacks=[CommandHandler("cancel", admin.cancel_conversation)],
        per_chat=True,
        per_user=True,
        per_message=False,
    )
    app.add_handler(admin_bulk_add_conv)

    # 6. Core Commands
    app.add_handler(CommandHandler("start", handlers.start_handler))
    app.add_handler(CommandHandler("admin", admin.admin_panel_handler))
    app.add_handler(CommandHandler("help", handlers.menu_support_handler))

    # 7. Main Menu Keyboard Buttons
    app.add_handler(MessageHandler(filters.Regex("^🛒 BUY NUMBER$"), handlers.menu_buy_handler))
    app.add_handler(MessageHandler(filters.Regex("^📦 MY ORDERS$"), handlers.menu_my_orders_handler))
    app.add_handler(MessageHandler(filters.Regex("^📋 MY LISTINGS$"), handlers.menu_my_listings_handler))
    app.add_handler(MessageHandler(filters.Regex("^💳 WALLET$"), handlers.menu_wallet_handler))
    app.add_handler(MessageHandler(filters.Regex("^💵 EARNINGS$"), handlers.menu_earnings_handler))
    app.add_handler(MessageHandler(filters.Regex("^💱 CURRENCY$"), handlers.menu_currency_handler))
    app.add_handler(MessageHandler(filters.Regex("^👤 PROFILE$"), handlers.menu_profile_handler))
    app.add_handler(MessageHandler(filters.Regex("^📊 STATISTICS$"), handlers.menu_statistics_handler))
    app.add_handler(MessageHandler(filters.Regex("^❓ SUPPORT$"), handlers.menu_support_handler))
    app.add_handler(MessageHandler(filters.Regex("^🛠 ADMIN PANEL$"), admin.admin_panel_handler))

    # 8. Buy Flow Callbacks
    app.add_handler(CallbackQueryHandler(handlers.buy_country_selected_cb, pattern="^buy_country:"))
    app.add_handler(CallbackQueryHandler(handlers.buy_back_countries_cb, pattern="^buy_back_countries$"))
    app.add_handler(CallbackQueryHandler(handlers.buy_service_selected_cb, pattern="^buy_svc:"))
    app.add_handler(CallbackQueryHandler(handlers.buy_number_selected_cb, pattern="^buy_num:"))
    app.add_handler(CallbackQueryHandler(handlers.pay_confirm_cb, pattern="^pay_confirm:"))
    app.add_handler(CallbackQueryHandler(handlers.order_cancel_cb, pattern="^order_cancel:"))
    app.add_handler(CallbackQueryHandler(handlers.pay_cancel_cb, pattern="^pay_cancel$"))
    app.add_handler(CallbackQueryHandler(handlers.close_menu_cb, pattern="^close_menu$"))

    # 9. Currency Switcher Callbacks
    app.add_handler(CallbackQueryHandler(handlers.set_currency_callback, pattern="^set_curr:"))

    # 10. Admin Control Panel Callbacks
    app.add_handler(CallbackQueryHandler(admin.admin_inventory_handler, pattern="^adm:inventory"))
    app.add_handler(CallbackQueryHandler(admin.admin_manage_num_handler, pattern="^adm_manage_num:"))
    app.add_handler(CallbackQueryHandler(admin.admin_toggle_num_status, pattern="^adm_num_toggle:"))
    app.add_handler(CallbackQueryHandler(admin.admin_delete_num, pattern="^adm_num_del:"))
    app.add_handler(CallbackQueryHandler(admin.admin_listings_handler, pattern="^adm:listings$"))
    app.add_handler(CallbackQueryHandler(admin.admin_approve_listing_cb, pattern="^adm_appr_list:"))
    app.add_handler(CallbackQueryHandler(admin.admin_reject_listing_cb, pattern="^adm_rej_list:"))
    app.add_handler(CallbackQueryHandler(admin.admin_users_handler, pattern="^adm:users"))
    app.add_handler(CallbackQueryHandler(admin.admin_toggle_user_ban, pattern="^adm_user_ban:"))
    app.add_handler(CallbackQueryHandler(admin.admin_orders_handler, pattern="^adm:orders"))
    app.add_handler(CallbackQueryHandler(admin.admin_payments_handler, pattern="^adm:payments"))
    app.add_handler(CallbackQueryHandler(admin.admin_payouts_handler, pattern="^adm:payouts$"))
    app.add_handler(CallbackQueryHandler(admin.admin_payout_action_cb, pattern="^adm_payout_"))
    app.add_handler(CallbackQueryHandler(admin.admin_panel_handler, pattern="^adm:stats$"))
    app.add_handler(CallbackQueryHandler(admin.admin_settings_handler, pattern="^adm:settings$"))
    app.add_handler(CallbackQueryHandler(admin.admin_set_commission_cb, pattern="^adm_set_comm:"))
    app.add_handler(CallbackQueryHandler(handlers.close_menu_cb, pattern="^adm:close$"))

    bot_app = app
    return app


async def notify_user_order_fulfilled(bot, payload: dict) -> None:
    """Delivers purchased number details to buyer via Telegram."""
    buyer_tid = payload.get("buyer_telegram_id")
    if not buyer_tid:
        return

    sym = "₹" if payload["currency"] == "INR" else "$"
    text = (
        "━━━━━━━━━━━━━━━━━━\n"
        "🎉 **PAYMENT CONFIRMED & DELIVERED**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Thank you for your purchase!\n"
        f"🆔 **Order ID**: `{payload['order_id']}`\n\n"
        "📱 **YOUR AUTHORIZED VIRTUAL NUMBER**:\n"
        f"👉 `{payload['number']}`\n\n"
        f"🌍 **Country**: {payload['country']}\n"
        f"⚡ **Service**: {payload['service']}\n"
        f"💰 **Amount Paid**: {sym}{payload['amount']:.2f} {payload['currency']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "You can view this anytime under **📦 MY ORDERS**."
    )
    try:
        await bot.send_message(chat_id=buyer_tid, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.error("Failed to deliver fulfilled order message to buyer %s: %s", buyer_tid, e)

    # If seller exists, notify seller of sale
    seller_info = payload.get("seller_info")
    if seller_info and seller_info.get("seller_telegram_id"):
        seller_tid = seller_info["seller_telegram_id"]
        seller_sym = "₹" if seller_info["currency"] == "INR" else "$"
        seller_text = (
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 **INVENTORY ITEM SOLD!**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"Your authorized number `{payload['number']}` has been purchased!\n\n"
            f"💵 **Net Earning**: {seller_sym}{seller_info['seller_net']:.2f} {seller_info['currency']}\n"
            f"📈 (Marketplace Commission deducted: {seller_sym}{seller_info['commission']:.2f})\n\n"
            "Funds have been deposited to your **💳 WALLET** and are available for withdrawal."
        )
        try:
            await bot.send_message(chat_id=seller_tid, text=seller_text, parse_mode="Markdown")
        except Exception as e:
            logger.error("Failed to notify seller %s of purchase: %s", seller_tid, e)
