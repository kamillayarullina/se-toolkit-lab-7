# Bot Dockerfile - uses uv for dependency management
FROM python:3.14.2-slim

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy pyproject.toml and uv.lock first (for layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy the bot code
COPY bot/ ./bot/

# Set environment variables
ENV PYTHONUNBUFFERED=1
WORKDIR /app/bot

# Run the bot
CMD ["uv", "run", "bot.py"]
