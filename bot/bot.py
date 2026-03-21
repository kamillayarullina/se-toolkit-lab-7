#!/usr/bin/env python3
import sys
import argparse
import logging
from handlers.commands import handle_start, handle_help, handle_health, handle_labs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COMMAND_HANDLERS = {
    "/start": handle_start,
    "/help": handle_help,
    "/health": handle_health,
    "/labs": handle_labs,
}

def process_command(command: str) -> str:
    parts = command.strip().split()
    if not parts:
        return "No command provided."

    cmd = parts[0].lower()
    args = parts[1:]

    handler = COMMAND_HANDLERS.get(cmd)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            logger.exception(f"Error handling {cmd}")
            return f"Error processing command: {e}"
    else:
        return f"Unknown command: {cmd}. Use /help for available commands."

def test_mode(command: str) -> None:
    response = process_command(command)
    print(response)
    sys.exit(0)

def main() -> None:
    parser = argparse.ArgumentParser(description="SE Toolkit Bot")
    parser.add_argument("--test", help="Run in test mode with the given command")
    args = parser.parse_args()

    if args.test:
        test_mode(args.test)
    else:
        print("Normal Telegram mode not implemented yet. Use --test to test handlers.")
        sys.exit(1)

if __name__ == "__main__":
    main()