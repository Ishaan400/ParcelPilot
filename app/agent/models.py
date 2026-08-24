"""Structured agent response models."""

from typing import Any

from pydantic import BaseModel, Field


class ConfirmationRequest(BaseModel):
    """Recommended state-changing action. Never executed by the agent."""

    action_type: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    requires_user_confirmation: bool = True
    executed: bool = False


class ToolTrace(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    error: str | None = None


class AgentResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    confirmation: ConfirmationRequest | None = None
    tool_trace: list[ToolTrace] = Field(default_factory=list)
    error: str | None = None
