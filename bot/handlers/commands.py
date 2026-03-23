def handle_start(args: list[str]) -> str:
    return "Welcome to the SE Toolkit Bot! Use /help to see available commands."

def handle_help(args: list[str]) -> str:
    return "Available commands:\n/start - Welcome message\n/help - Show this help\n/health - Check backend health\n/labs - List available labs"

def handle_health(args: list[str]) -> str:
    return "Backend status: OK (placeholder)"

def handle_labs(args: list[str]) -> str:
    return "Available labs: lab-04, lab-05, lab-06 (placeholder)"