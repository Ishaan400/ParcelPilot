"""Helpers for the Streamlit UI. No Streamlit dependency."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx

DEFAULT_API_URL = "http://127.0.0.1:8000"


def new_session_id() -> str:
    return str(uuid4())


def build_chat_payload(
    message: str,
    session_id: str | None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    if history:
        payload["history"] = history
    return payload


def history_from_turns(turns: list[dict[str, Any]]) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for turn in turns:
        role = turn.get("role")
        content = turn.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            history.append({"role": role, "content": content})
    return history


def confirmation_is_pending(turn: dict[str, Any]) -> bool:
    confirmation = turn.get("confirmation")
    status = turn.get("confirmation_status")
    return bool(confirmation) and status is None


def confirmation_headline(confirmation: dict[str, Any] | None) -> str:
    if not confirmation:
        return ""
    action = confirmation.get("action_type") or "action"
    summary = confirmation.get("summary") or ""
    return f"{action}: {summary}".strip()


def format_api_failure(status_code: int | None, detail: str | None) -> str:
    if status_code is None:
        return "The ParcelPilot API is unavailable. Start the FastAPI backend and try again."
    if status_code == 422:
        return "The request was invalid. Enter a non-empty message."
    text = (detail or "").strip() or f"HTTP {status_code}"
    return f"The support API returned an error ({status_code}): {text}"


def empty_answer_fallback(answer: str | None, error: str | None) -> str:
    if error:
        return answer.strip() if answer and answer.strip() else "The agent reported an error."
    if answer and answer.strip():
        return answer
    return "The agent returned an empty response."


def post_chat(
    api_url: str,
    payload: dict[str, Any],
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    url = api_url.rstrip("/") + "/chat"
    try:
        response = httpx.post(url, json=payload, timeout=timeout_seconds)
    except httpx.RequestError:
        return {
            "ok": False,
            "status_code": None,
            "body": None,
            "error": format_api_failure(None, None),
        }

    try:
        body = response.json()
    except ValueError:
        body = None

    if response.is_success and isinstance(body, dict):
        return {"ok": True, "status_code": response.status_code, "body": body, "error": None}

    detail: str | None = None
    if isinstance(body, dict):
        raw = body.get("detail", body.get("error"))
        detail = raw if isinstance(raw, str) else str(raw) if raw is not None else None
    elif isinstance(body, str):
        detail = body

    return {
        "ok": False,
        "status_code": response.status_code,
        "body": body,
        "error": format_api_failure(response.status_code, detail),
    }
