"""
API request and response models for the Browser-Use Agent API.

Defines the Pydantic schemas used at the HTTP boundary for all
agent endpoint requests and responses.
"""
import logging

from pydantic import BaseModel, Field
from typing import Optional, List

logger = logging.getLogger(__name__)


class AgentRequest(BaseModel):
    """
    Request body for submitting a browser agent task.

    Attributes:
        task: Natural-language instruction for the browser agent.
        extend_system_message: Optional extra instructions appended to the
            agent's system prompt to enforce stop rules or behaviour
            constraints.
        allowed_domains: Optional whitelist of domains the browser may visit.
            Supports wildcard prefixes (e.g. ``*.example.com``).
        prohibited_domains: Optional blacklist of domains the browser must
            never visit. Supports wildcard prefixes.
    """

    task: str = Field(
        ...,
        description="The task/instruction for the browser agent. Go to https://www.google.com/ and find the top 10 pages of xbox.",
        example=""
    )
    extend_system_message: Optional[str] = Field(
        default=None,
        description="Extra system-level instructions appended to the agent's prompt.",
        example="Extra system-level instructions appended to the agent's prompt."
    )
    allowed_domains: Optional[List[str]] = Field(
        default=None,
        description="Whitelist of domains the browser is allowed to visit. ['*.google.com', 'example.com']",
        example=[]
    )
    prohibited_domains: Optional[List[str]] = Field(
        default=None,
        description="Blacklist of domains the browser must never visit. ['facebook.com']",
        example=[]
    )


class AgentResponse(BaseModel):
    """
    Response body returned by all agent execution endpoints.

    Attributes:
        success: Whether the agent completed the task without an unhandled
            error.
        final_url: The last meaningful URL visited by the browser agent.
            ``None`` if the agent failed before navigating anywhere.
        llm_result: Final text result returned by the LLM agent.
            ``None`` on failure.
        error: Human-readable error message if ``success`` is ``False``.
            ``None`` on success.
    """

    success: bool
    final_url: Optional[str] = Field(None, description="The last meaningful URL visited by the browser agent")
    llm_result: Optional[str] = Field(None, description="Final text result returned by the LLM agent")
    error: Optional[str] = Field(None, description="Error message if the agent failed")
