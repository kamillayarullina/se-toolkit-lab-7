import os
import sys
import logging
import json
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env.bot.secret')

# Backend configuration
LMS_API_KEY = os.getenv("LMS_API_KEY")
if not LMS_API_KEY:
    # fallback: read from .env.docker.secret in parent directory
    try:
        with open("../.env.docker.secret") as f:
            for line in f:
                if line.startswith("LMS_API_KEY="):
                    LMS_API_KEY = line.strip().split("=", 1)[1]
                    break
    except:
        pass
BASE_URL = "http://localhost:42002"

# LLM configuration
LLM_API_KEY = os.getenv("LLM_API_KEY") or "dummy"
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL") or "http://localhost:42005/v1"
LLM_API_MODEL = os.getenv("LLM_API_MODEL") or "qwen-plus"

# Initialize OpenAI client (Qwen-compatible)
client = openai.AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE_URL)

# ---------------------------
# Helper: call backend
# ---------------------------
async def call_backend(endpoint: str, method: str = "GET", params: dict = None, data: dict = None):
    """Make a request to the backend. Returns JSON data or dict with 'error'."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {LMS_API_KEY}"}
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=data, timeout=10)
            else:
                return {"error": f"Unsupported method {method}"}
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
# Tool definitions for LLM
# ---------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "Get list of all labs and tasks in the system",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "Get list of enrolled students and groups",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution (4 buckets) for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get submissions per day for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get per-group scores and student counts for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get top N learners by score for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"},
                    "limit": {"type": "integer", "description": "Number of learners to return (default 5)"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get completion rate percentage for a lab",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {"type": "string", "description": "Lab identifier, e.g. 'lab-04'"}
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Refresh data from autochecker (ETL sync)",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

async def call_tool(name: str, arguments: dict) -> str:
    """Execute a tool call and return a string representation of the result."""
    if name == "get_items":
        result = await call_backend("/items/")
    elif name == "get_learners":
        result = await call_backend("/learners/")
    elif name == "get_scores":
        lab = arguments.get("lab")
        if not lab:
            return "Error: missing lab parameter"
        result = await call_backend("/analytics/scores", params={"lab": lab})
    elif name == "get_pass_rates":
        lab = arguments.get("lab")
        if not lab:
            return "Error: missing lab parameter"
        result = await call_backend("/analytics/pass-rates", params={"lab": lab})
    elif name == "get_timeline":
        lab = arguments.get("lab")
        if not lab:
            return "Error: missing lab parameter"
        result = await call_backend("/analytics/timeline", params={"lab": lab})
    elif name == "get_groups":
        lab = arguments.get("lab")
        if not lab:
            return "Error: missing lab parameter"
        result = await call_backend("/analytics/groups", params={"lab": lab})
    elif name == "get_top_learners":
        lab = arguments.get("lab")
        limit = arguments.get("limit", 5)
        if not lab:
            return "Error: missing lab parameter"
        result = await call_backend("/analytics/top-learners", params={"lab": lab, "limit": limit})
    elif name == "get_completion_rate":
        lab = arguments.get("lab")
        if not lab:
            return "Error: missing lab parameter"
        result = await call_backend("/analytics/completion-rate", params={"lab": lab})
    elif name == "trigger_sync":
        result = await call_backend("/pipeline/sync", method="POST", data={})
    else:
        return f"Unknown tool: {name}"

    if isinstance(result, dict) and "error" in result:
        return f"Error: {result['error']}"
    # Convert to compact JSON string for LLM
    return json.dumps(result, ensure_ascii=False, indent=2)

# ---------------------------
# System prompt
# ---------------------------
SYSTEM_PROMPT = """You are an assistant for an LMS system. You have access to several tools to retrieve data about labs, students, and analytics. Use these tools to answer the user's question. If the user asks a question that requires multiple steps, call the necessary tools one after another. When you have enough data, provide a clear and helpful answer. If the user's input is unclear, ask for clarification or suggest what you can help with."""

async def route(user_message: str) -> str:
    """Process user message using LLM with tool calling."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # Loop for multi-step reasoning
    while True:
        response = await client.chat.completions.create(
            model=LLM_API_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        choice = response.choices[0]
        if choice.finish_reason == "tool_calls":
            # Add assistant's tool call message to history
            messages.append(choice.message.model_dump())
            # Execute each tool call
            for tool_call in choice.message.tool_calls:
                name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                # Debug output
                print(f"[tool] LLM called: {name}({arguments})", file=sys.stderr)
                result = await call_tool(name, arguments)
                print(f"[tool] Result: {result[:200]}", file=sys.stderr)
                # Add tool result message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
            # Continue loop to let LLM process results
            continue
        else:
            # Final answer
            final_text = choice.message.content or "I couldn't generate a response."
            return final_text

# ---------------------------
# Command handlers
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Keyboard with inline buttons
    keyboard = [
        [InlineKeyboardButton("📚 List labs", callback_data="what labs are available")],
        [InlineKeyboardButton("📊 Scores for Lab 04", callback_data="show me scores for lab 04")],
        [InlineKeyboardButton("🏆 Lowest pass rate lab", callback_data="which lab has the lowest pass rate")],
        [InlineKeyboardButton("👥 Top 5 students in Lab 04", callback_data="who are the top 5 students in lab 4")],
        [InlineKeyboardButton("❓ Help", callback_data="/help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to the LMS Bot! I can answer questions about labs, scores, and more.\n\n"
        "Try typing a question or use the buttons below:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "I'm an AI assistant for the LMS. You can ask me questions like:\n"
        "- What labs are available?\n"
        "- Show me scores for lab 04\n"
        "- Which lab has the lowest pass rate?\n"
        "- Who are the top 5 students in lab 4?\n"
        "- How many students are enrolled?\n"
        "- Compare group A and group B in lab 3\n\n"
        "Just type your question, and I'll fetch the data!"
    )
    await update.message.reply_text(help_text)

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await call_backend("/items/")
    if "error" in data:
        await update.message.reply_text(f"⚠️ Backend error: {data['error']}. Check that the services are running.")
    else:
        item_count = len(data)
        await update.message.reply_text(f"Backend is healthy. {item_count} items available.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (non-command)."""
    user_text = update.message.text
    try:
        answer = await route(user_text)
        await update.message.reply_text(answer)
    except Exception as e:
        logging.exception("Error in route")
        await update.message.reply_text("Sorry, I encountered an error while processing your request.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses."""
    query = update.callback_query
    await query.answer()
    # Get the query text
    prompt = query.data
    if prompt == "/help":
        await help_command(update, context)
        return
    # Send a thinking message
    await query.edit_message_text(f"Processing: {prompt} ...")
    try:
        answer = await route(prompt)
        await query.edit_message_text(answer)
    except Exception as e:
        await query.edit_message_text("Sorry, I encountered an error while processing your request.")

# ---------------------------
# Main
# ---------------------------
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN not set. Exiting.")
        sys.exit(1)

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("health", health))
    # Text handler (non-command)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    # Inline button handler
    application.add_handler(CallbackQueryHandler(button_callback))

    application.run_polling()

if __name__ == "__main__":
    # Test mode: if --test is present, treat the next argument as a user message
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        import asyncio
        if len(sys.argv) < 3:
            print("Usage: uv run bot.py --test \"<message>\"")
            sys.exit(1)
        test_message = sys.argv[2]
        async def run_test():
            print("--- Running test mode ---", file=sys.stderr)
            answer = await route(test_message)
            print(answer)
        asyncio.run(run_test())
    else:
        main()