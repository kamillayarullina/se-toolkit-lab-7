# Development Plan for SE Toolkit Bot

## Overview
This bot will serve as a Telegram interface to the SE Toolkit lab. It will allow users to query backend data (like lab scores), get help, and eventually interact with an LLM for natural language queries.

## Phase 1: Scaffold (Task 1)
- Create bot directory structure with handlers, services, and configuration.
- Implement test mode: handlers return simple strings, no Telegram dependency.
- Set up `uv` with `pyproject.toml` for dependency management.
- Provide environment variable templates.

## Phase 2: Backend Integration (Task 2)
- Replace placeholder handlers with actual API calls to the backend.
- Handle `/health` by pinging backend, `/labs` by fetching lab list.
- Use LMS API client in `services/` to encapsulate HTTP requests.

## Phase 3: Intent Routing (Task 3)
- Implement a generic message handler that forwards text to an LLM.
- The LLM will classify intent and return appropriate responses (e.g., "list labs", "get scores for lab-04").
- Fallback to a default answer if intent is unclear.

## Phase 4: Deployment and Testing
- Use Docker Compose to run the bot alongside backend and frontend.
- Ensure the bot can start via `uv run bot.py` and connect to Telegram.
- Verify end-to-end functionality with real commands.

## Risks and Mitigations
- API rate limits: implement caching if needed.
- LLM cost: use efficient prompts and consider fallback.
- Environment secrets: store in `.env.bot.secret` and never commit.