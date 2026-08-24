"""Safe error strings for clients. Raw SDK exceptions stay server-side."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("parcelpilot")

PUBLIC_LLM_ERROR = "language_model_error"
PUBLIC_LLM_ANSWER = (
    "I could not complete the request because the language-model API call failed."
)
PUBLIC_CLIENT_CREATE_ANSWER = "The language-model client could not be created."

_SECRET_RE = re.compile(
    r"api[_-]?key|authorization|bearer\s+\S+|sk-[A-Za-z0-9_-]{8,}|"
    r"credential|secret|x-api-key",
    re.IGNORECASE,
)


def redact_public_error(raw: str | None) -> str | None:
    """Return a client-safe error token. Never include secrets or SDK dumps."""
    if raw is None:
        return None
    if _SECRET_RE.search(raw) or "Traceback" in raw or len(raw) > 180:
        return PUBLIC_LLM_ERROR
    return raw


def log_and_redact(exc: BaseException) -> str:
    logger.exception("Language-model or API failure")
    return redact_public_error(str(exc)) or PUBLIC_LLM_ERROR
