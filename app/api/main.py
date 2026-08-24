"""FastAPI application entry point."""

from fastapi import Depends, FastAPI, HTTPException

from app.agent.agent import SupportAgent
from app.agent.errors import log_and_redact, redact_public_error
from app.agent.models import AgentResponse
from app.api.deps import get_agent
from app.api.schemas import ChatRequest, ChatResponse

app = FastAPI(title="ParcelPilot Support Agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _to_chat_response(result: AgentResponse, session_id: str | None) -> ChatResponse:
    return ChatResponse(
        answer=result.answer,
        sources=result.sources,
        confirmation=result.confirmation,
        tool_trace=result.tool_trace,
        error=redact_public_error(result.error),
        session_id=session_id,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, agent: SupportAgent = Depends(get_agent)) -> ChatResponse:
    try:
        result = agent.run(payload.message, history=payload.history)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=log_and_redact(exc)) from exc
    return _to_chat_response(result, payload.session_id)
