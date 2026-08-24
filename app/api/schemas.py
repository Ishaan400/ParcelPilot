"""HTTP request and response models for the chat API."""

from typing import Any

from pydantic import BaseModel, Field

from app.agent.models import ConfirmationRequest, ToolTrace


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    history: list[dict[str, Any]] | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    confirmation: ConfirmationRequest | None = None
    tool_trace: list[ToolTrace] = Field(default_factory=list)
    error: str | None = None
    session_id: str | None = None
