import asyncio
import json
import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Load initial config
# ---------------------------------------------------------------------------
config = load_config()

# Token: environment variable takes priority over config file so the token
# is never required to be committed to source control.
BOT_TOKEN: str = os.environ.get("BOT_TOKEN") or config.get("bot_token", "")
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise RuntimeError(
        "Bot token not set. Either set the BOT_TOKEN environment variable or "
        "fill in 'bot_token' in config.json."
    )

OWNER_ID: int = int(os.environ.get("OWNER_ID") or config.get("owner_id", 0))
if not OWNER_ID:
    raise RuntimeError(
        "Owner ID not set. Either set the OWNER_ID environment variable or "
        "fill in 'owner_id' in config.json."
    )

# ---------------------------------------------------------------------------
# Owner-only guard
# ---------------------------------------------------------------------------

def owner_only(func):
    """Decorator: reject commands from anyone who is not the owner."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user and update.effective_user.id != OWNER_ID:
            await update.message.reply_text("⛔ You are not authorized to use this command.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__  # preserve name for handler registration
    return wrapper


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *Personal Ads Bot*\n\n"
        "Available commands (owner only):\n"
        "/addgroup `<group_id>` — add a group to the send list\n"
        "/removegroup `<group_id>` — remove a group from the send list\n"
        "/listgroups — show all selected groups\n"
        "/setmessage `<text>` — set the promo message\n"
        "/setaway `<text>` — set the away-reply message\n"
        "/setinterval `<minutes>` — set auto-send interval\n"
        "/online — mark yourself as online (disables auto-reply)\n"
        "/offline — mark yourself as offline (enables auto-reply)\n"
        "/send — send promo message to all selected groups now\n"
        "/status — show current settings\n",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Group management
# ---------------------------------------------------------------------------

@owner_only
async def cmd_addgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    if not context.args:
        await update.message.reply_text("Usage: /addgroup <group_id>")
        return
    raw = context.args[0].strip()
    # Accept negative IDs (supergroups) with or without the leading minus sign
    try:
        group_id = int(raw)
    except ValueError:
        await update.message.reply_text("❌ Invalid group ID. It must be a number (e.g. -1001234567890).")
        return
    groups: list = cfg.get("selected_groups", [])
    if group_id in groups:
        await update.message.reply_text(f"ℹ️ Group `{group_id}` is already in the list.", parse_mode="Markdown")
        return
    groups.append(group_id)
    cfg["selected_groups"] = groups
    save_config(cfg)
    await update.message.reply_text(f"✅ Group `{group_id}` added.", parse_mode="Markdown")


@owner_only
async def cmd_removegroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    if not context.args:
        await update.message.reply_text("Usage: /removegroup <group_id>")
        return
    try:
        group_id = int(context.args[0].strip())
    except ValueError:
        await update.message.reply_text("❌ Invalid group ID.")
        return
    groups: list = cfg.get("selected_groups", [])
    if group_id not in groups:
        await update.message.reply_text(f"ℹ️ Group `{group_id}` is not in the list.", parse_mode="Markdown")
        return
    groups.remove(group_id)
    cfg["selected_groups"] = groups
    save_config(cfg)
    await update.message.reply_text(f"✅ Group `{group_id}` removed.", parse_mode="Markdown")


@owner_only
async def cmd_listgroups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    groups = cfg.get("selected_groups", [])
    if not groups:
        await update.message.reply_text("📋 No groups selected yet.")
        return
    lines = "\n".join(f"• `{g}`" for g in groups)
    await update.message.reply_text(f"📋 *Selected groups:*\n{lines}", parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Message / away config
# ---------------------------------------------------------------------------

@owner_only
async def cmd_setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    if not context.args:
        await update.message.reply_text("Usage: /setmessage <your promo message text>")
        return
    text = " ".join(context.args)
    cfg["promo_message"] = text
    save_config(cfg)
    await update.message.reply_text(f"✅ Promo message updated:\n\n{text}")


@owner_only
async def cmd_setaway(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    if not context.args:
        await update.message.reply_text("Usage: /setaway <your away message text>")
        return
    text = " ".join(context.args)
    cfg["away_message"] = text
    save_config(cfg)
    await update.message.reply_text(f"✅ Away message updated:\n\n{text}")


@owner_only
async def cmd_setinterval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    if not context.args:
        await update.message.reply_text("Usage: /setinterval <minutes>")
        return
    try:
        minutes = int(context.args[0])
        if minutes < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Please provide a positive integer (minutes).")
        return
    cfg["send_interval_minutes"] = minutes
    save_config(cfg)

    # Remove old job and schedule a new one with the updated interval
    current_jobs = context.job_queue.get_jobs_by_name("auto_send")
    for job in current_jobs:
        job.schedule_removal()
    context.job_queue.run_repeating(
        auto_send_job,
        interval=minutes * 60,
        first=minutes * 60,
        name="auto_send",
    )

    await update.message.reply_text(f"✅ Auto-send interval updated to {minutes} minute(s). New schedule is active.")


# ---------------------------------------------------------------------------
# Online / Offline toggle
# ---------------------------------------------------------------------------

@owner_only
async def cmd_online(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    cfg["owner_online"] = True
    save_config(cfg)
    await update.message.reply_text("✅ You are now marked as *online*. Auto-reply is disabled.", parse_mode="Markdown")


@owner_only
async def cmd_offline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    cfg["owner_online"] = False
    save_config(cfg)
    await update.message.reply_text("✅ You are now marked as *offline*. Auto-reply is enabled.", parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Manual send
# ---------------------------------------------------------------------------

@owner_only
async def cmd_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    groups = cfg.get("selected_groups", [])
    message = cfg.get("promo_message", "")
    if not groups:
        await update.message.reply_text("❌ No groups selected. Use /addgroup first.")
        return
    if not message:
        await update.message.reply_text("❌ No promo message set. Use /setmessage first.")
        return
    sent, failed = 0, 0
    for gid in groups:
        try:
            await context.bot.send_message(chat_id=gid, text=message)
            sent += 1
        except Exception as exc:
            logger.error("Failed to send to group %s: %s", gid, exc)
            failed += 1
        await asyncio.sleep(1)  # avoid Telegram rate limits
    await update.message.reply_text(
        f"📤 Done.\n✅ Sent: {sent}\n❌ Failed: {failed}"
    )


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@owner_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = load_config()
    groups = cfg.get("selected_groups", [])
    promo = cfg.get("promo_message", "(not set)")
    away = cfg.get("away_message", "(not set)")
    interval = cfg.get("send_interval_minutes", 60)
    online = cfg.get("owner_online", True)
    status_icon = "🟢 Online" if online else "🔴 Offline"
    group_list = ", ".join(str(g) for g in groups) if groups else "none"
    await update.message.reply_text(
        f"*📊 Bot Status*\n\n"
        f"*Owner status:* {status_icon}\n"
        f"*Auto-send interval:* {interval} min\n"
        f"*Selected groups:* {group_list}\n\n"
        f"*Promo message:*\n{promo}\n\n"
        f"*Away message:*\n{away}",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Auto-reply to private messages when owner is offline
# ---------------------------------------------------------------------------

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the away message when a user DMs the bot and owner is offline."""
    cfg = load_config()
    # Do not auto-reply to the owner themselves
    if update.effective_user and update.effective_user.id == OWNER_ID:
        return
    if not cfg.get("owner_online", True):
        away = cfg.get("away_message", "The owner is currently offline. Please try again later.")
        await update.message.reply_text(away)
        # Notify the owner about the incoming message
        try:
            sender = update.effective_user
            name = sender.full_name if sender else "Unknown"
            username = f"@{sender.username}" if sender and sender.username else "no username"
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=(
                    f"📩 *New message while offline*\n"
                    f"From: {name} ({username}, `{sender.id}`)\n\n"
                    f"{update.message.text}"
                ),
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.error("Could not forward message to owner: %s", exc)


# ---------------------------------------------------------------------------
# Periodic auto-send job
# ---------------------------------------------------------------------------

async def auto_send_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job callback: send promo message to all selected groups."""
    cfg = load_config()
    groups = cfg.get("selected_groups", [])
    message = cfg.get("promo_message", "")
    if not groups or not message:
        return
    for gid in groups:
        try:
            await context.bot.send_message(chat_id=gid, text=message)
            logger.info("Auto-sent promo to group %s", gid)
        except Exception as exc:
            logger.error("Auto-send failed for group %s: %s", gid, exc)
        await asyncio.sleep(1)  # avoid Telegram rate limits


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = load_config()
    interval_minutes = cfg.get("send_interval_minutes", 60)

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("addgroup", cmd_addgroup))
    app.add_handler(CommandHandler("removegroup", cmd_removegroup))
    app.add_handler(CommandHandler("listgroups", cmd_listgroups))
    app.add_handler(CommandHandler("setmessage", cmd_setmessage))
    app.add_handler(CommandHandler("setaway", cmd_setaway))
    app.add_handler(CommandHandler("setinterval", cmd_setinterval))
    app.add_handler(CommandHandler("online", cmd_online))
    app.add_handler(CommandHandler("offline", cmd_offline))
    app.add_handler(CommandHandler("send", cmd_send))
    app.add_handler(CommandHandler("status", cmd_status))

    # Auto-reply for private messages (non-command text)
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, handle_private_message)
    )

    # Periodic job: send promo to selected groups
    app.job_queue.run_repeating(
        auto_send_job,
        interval=interval_minutes * 60,
        first=interval_minutes * 60,
        name="auto_send",
    )

    logger.info("Bot started. Polling for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
