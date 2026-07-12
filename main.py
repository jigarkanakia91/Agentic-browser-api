from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from models import AgentRequest, AgentResponse
from agent_runner import run_agent

logger = logging.getLogger(__name__)


class BrowAgentRequest(BaseModel):
    """
    Request body for submitting an browser agent task.

    """


MAX_CONCURRENT_AGENTS = 3
_semaphore: asyncio.Semaphore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise and tear down application-scoped resources."""
    global _semaphore
    _semaphore = asyncio.Semaphore(MAX_CONCURRENT_AGENTS)
    yield


app = FastAPI(title="Browser-Use Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Return API health status."""
    return {"status": "ok"}


@app.post("/run-agent", response_model=AgentResponse, tags=["Agent"])
async def run_agent_endpoint(request: AgentRequest) -> AgentResponse:
    """
    Run a browser agent task from a free-form request.

    Args:
        request: Agent task request containing the instruction and optional
            domain filters and system message extension.

    Returns:
        AgentResponse: Result of the agent run including the final URL
            and LLM output.

    Raises:
        HTTPException 500: If the agent fails to complete the task.
    """
    async with _semaphore:
        result = await run_agent(
            task=request.task,
            extend_system_message=request.extend_system_message,
            allowed_domains=request.allowed_domains,
            prohibited_domains=request.prohibited_domains,
        )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return AgentResponse(
        success=result["success"],
        final_url=result["final_url"],
        llm_result=result["llm_result"],
    )

