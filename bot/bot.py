import os
import sys
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables (if using .env)
from dotenv import load_dotenv
load_dotenv()

# Backend configuration
LMS_API_KEY = os.getenv("dummy")
BASE_URL = "http://localhost:42002"

# ---------------------------
# Helper: call backend
# ---------------------------
async def call_backend(endpoint: str, params: dict = None):
    """Make a GET request to the backend. Returns JSON data or dict with 'error'."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {LMS_API_KEY}"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=5)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code} {e.response.reason_phrase}"}
    except httpx.ConnectError:
        return {"error": "connection refused – backend not running"}
    except httpx.TimeoutException:
        return {"error": "request timed out"}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------
# Command handlers
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the LMS Bot! Use /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Available commands:\n"
        "/start – welcome message\n"
        "/help – show this help\n"
        "/health – check backend status\n"
        "/labs – list available labs\n"
        "/scores <lab> – show pass rates for a lab (e.g., /scores lab-04)"
    )
    await update.message.reply_text(help_text)

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await call_backend("/items/")
    if "error" in data:
        await update.message.reply_text(
            f"⚠️ Backend error: {data['error']}. Check that the services are running."
        )
    else:
        item_count = len(data)
        await update.message.reply_text(f"✅ Backend is healthy. {item_count} items available.")

async def labs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await call_backend("/items/")
    if "error" in data:
        await update.message.reply_text(
            f"⚠️ Backend error: {data['error']}. Cannot fetch labs."
        )
        return

    # Filter items that are labs (adjust field names based on actual backend response)
    # Common patterns: type == 'lab' or category == 'lab'
    labs_list = [item for item in data if item.get("type") == "lab" or item.get("category") == "lab"]
    if not labs_list:
        await update.message.reply_text("No labs found.")
        return

    msg = "Available labs:\n"
    for lab in labs_list:
        # Use fields that exist in your backend (name, title, id, etc.)
        name = lab.get("name") or lab.get("title") or "Unnamed"
        lab_id = lab.get("id") or lab.get("lab_id") or "unknown"
        msg += f"- {lab_id} — {name}\n"
    await update.message.reply_text(msg.strip())

async def scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify a lab, e.g., /scores lab-04")
        return

    lab = context.args[0]
    data = await call_backend("/analytics/pass-rates/", params={"lab": lab})
    if "error" in data:
        await update.message.reply_text(
            f"⚠️ Backend error: {data['error']}. Could not get scores for {lab}."
        )
        return

    if not data:
        await update.message.reply_text(f"No data for lab {lab}.")
        return

    msg = f"Pass rates for {lab}:\n"
    for task in data:
        task_name = task.get("task") or task.get("name") or "Unknown task"
        pass_rate = task.get("pass_rate", 0)
        attempts = task.get("attempts", 0)
        # If pass_rate is a fraction (0.0-1.0), convert to percentage
        if 0 <= pass_rate <= 1:
            pass_rate *= 100
        msg += f"- {task_name}: {pass_rate:.1f}% ({attempts} attempts)\n"
    await update.message.reply_text(msg.strip())

# ---------------------------
# Main
# ---------------------------
def main():
    # Read Telegram bot token from environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN not set. Exiting.")
        sys.exit(1)

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("health", health))
    application.add_handler(CommandHandler("labs", labs))
    application.add_handler(CommandHandler("scores", scores))

    # Start polling (or run test mode)
    application.run_polling()

if __name__ == "__main__":
    # Test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        class DummyUpdate:
            message = MagicMock()
            message.reply_text = AsyncMock()

        class DummyContext:
            args = sys.argv[2:] if len(sys.argv) > 2 else []

        async def run_test():
            cmd = sys.argv[2] if len(sys.argv) > 2 else "/start"
            update = DummyUpdate()
            context = DummyContext()
            if cmd == "/start":
                await start(update, context)
            elif cmd == "/help":
                await help_command(update, context)
            elif cmd == "/health":
                await health(update, context)
            elif cmd == "/labs":
                await labs(update, context)
            elif cmd.startswith("/scores"):
                context.args = cmd.split()[1:]
                await scores(update, context)
            else:
                print("Unknown command. Use /start, /help, /health, /labs, /scores <lab>")
                return
            # Print the text that would be sent
            print(update.message.reply_text.call_args[0][0])

        asyncio.run(run_test())
    else:
        main()
