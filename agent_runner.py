"""
Browser agent execution service.

Manages thread-safe execution of browser-use AI agents. Each agent run is
isolated in its own OS thread with a dedicated event loop, ensuring complete
independence from Uvicorn's SelectorEventLoop on Windows.
"""

# 1. Standard library
import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# 2. Third-party
from browser_use import Agent, Browser, ChatOpenAI, Tools
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Sized to match MAX_CONCURRENT_AGENTS; will be driven by app_config once the
# config service is introduced (gap analysis item H-2).
_executor = ThreadPoolExecutor(max_workers=3)


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

async def _agent_task(
    task: str,
    extend_system_message: str | None,
    allowed_domains: list[str] | None,
    prohibited_domains: list[str] | None,
) -> dict[str, Any]:
    """
    Execute a single browser agent run inside a worker thread's event loop.

    Constructs the LLM client, browser instance, and agent from the supplied
    parameters, runs the agent to completion, and returns a normalised result dict.

    Args:
        task: Natural-language instruction for the agent.
        extend_system_message: Optional extra instructions appended to the
            agent's system prompt.
        allowed_domains: Optional whitelist of domains the browser may visit.
        prohibited_domains: Optional blacklist of domains the browser must not visit.

    Returns:
        dict[str, Any]: Keys ``success``, ``final_url``, ``llm_result``, ``error``.
    """
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", ""),
        api_key=os.getenv("NVIDIA_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        temperature=float(os.getenv("LLM_TEMPERATURE","0.2")),
    )

    tools = Tools(
        exclude_actions=["write_file", "read_file", "replace_file", "save_as_pdf"]
    )

    browser_kwargs: dict[str, Any] = dict(
        headless=False,
        ignore_default_args=["--extensions-on-chrome-urls"],
        channel="chrome",  # use real Chrome to avoid bot-detection fingerprinting
        enable_default_extensions=True,
        user_data_dir=os.getenv("BROWSER_USER_DATA_DIR"),  # persistent profile carries cookies/history
        user_agent=os.getenv(
            "BROWSER_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        ),
    )
    if allowed_domains:
        browser_kwargs["allowed_domains"] = allowed_domains
    if prohibited_domains:
        browser_kwargs["prohibited_domains"] = prohibited_domains

    browser = Browser(**browser_kwargs)

    # max_steps will move to app_config (gap analysis H-2).
    agent_kwargs: dict[str, Any] = dict(
        task=task,
        llm=llm,
        browser=browser,
        tools=tools,
        max_actions_per_step=1,
        enable_memory=True,
        max_steps=13,
    )
    if extend_system_message:
        agent_kwargs["extend_system_message"] = extend_system_message

    agent = Agent(**agent_kwargs)

    try:
        history = await agent.run()
        visited_urls: list[str] = history.urls()
        final_url = next((u for u in reversed(visited_urls) if u), None)
        return {
            "success": True,
            "final_url": final_url,
            "llm_result": history.final_result(),
            "error": None,
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Agent task failed: %s", str(exc), exc_info=True)
        return {
            "success": False,
            "final_url": None,
            "llm_result": None,
            "error": str(exc),
        }
    finally:
        try:
            if agent.browser_session:
                await agent.browser_session.stop()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Error stopping browser session: %s", str(exc))


def _run_in_thread(
    task: str,
    extend_system_message: str | None,
    allowed_domains: list[str] | None,
    prohibited_domains: list[str] | None,
) -> dict[str, Any]:
    """
    Run ``_agent_task`` inside a ThreadPoolExecutor worker.

    Creates a fresh event loop (ProactorEventLoop on Windows, default elsewhere)
    that is completely independent of Uvicorn's SelectorEventLoop, then tears it
    down cleanly when the task completes or raises.

    Args:
        task: Natural-language instruction for the agent.
        extend_system_message: Optional extra instructions for the agent's system prompt.
        allowed_domains: Optional whitelist of domains the browser may visit.
        prohibited_domains: Optional blacklist of domains the browser must not visit.

    Returns:
        dict[str, Any]: Result dict from ``_agent_task``.
    """
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()  # explicit Proactor required on Windows
    else:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(
            _agent_task(task, extend_system_message, allowed_domains, prohibited_domains)
        )
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Error shutting down async generators: %s", str(exc))
        loop.close()
        asyncio.set_event_loop(None)  # clear thread-local loop reference


# ------------------------------------------------------------------
# Public API — called from FastAPI route handlers
# ------------------------------------------------------------------

async def run_agent(
    task: str,
    extend_system_message: str | None = None,
    allowed_domains: list[str] | None = None,
    prohibited_domains: list[str] | None = None,
) -> dict[str, Any]:
    """
    Awaitable entry point for FastAPI route handlers.

    Offloads the blocking browser work to the shared thread executor so
    Uvicorn's event loop remains free to handle other HTTP requests.

    Args:
        task: Natural-language instruction for the agent.
        extend_system_message: Optional extra instructions for the agent's system prompt.
        allowed_domains: Optional whitelist of domains the browser may visit.
        prohibited_domains: Optional blacklist of domains the browser must not visit.

    Returns:
        dict[str, Any]: Keys ``success``, ``final_url``, ``llm_result``, ``error``.
    """
    uvicorn_loop = asyncio.get_running_loop()
    return await uvicorn_loop.run_in_executor(
        _executor,
        _run_in_thread,
        task,
        extend_system_message,
        allowed_domains,
        prohibited_domains,
    )
