"""
Application entry point for the Browser-Use Agent API.

Configures the Windows ProactorEventLoop policy before Uvicorn loads,
then starts the server. Run this file directly instead of invoking
uvicorn from the CLI so the event loop policy is applied first.
"""
import asyncio
import logging
import sys

# Must happen BEFORE uvicorn imports anything
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger("api")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,       # ← drop --reload; it spawns subprocesses that break the policy
        loop="asyncio",     # ← explicitly tell uvicorn to use asyncio loop
        workers=1,          # ← 1 worker since browser agents are heavy
    )
