"""ParcelPilot internal support UI. Talks only to the FastAPI /chat endpoint."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.ui.client import (
    DEFAULT_API_URL,
    build_chat_payload,
    confirmation_headline,
    confirmation_is_pending,
    empty_answer_fallback,
    history_from_turns,
    new_session_id,
    post_chat,
)


def _init_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = new_session_id()
    if "turns" not in st.session_state:
        st.session_state.turns = []
    if "show_tool_trace" not in st.session_state:
        st.session_state.show_tool_trace = True


def _clear_conversation() -> None:
    st.session_state.session_id = new_session_id()
    st.session_state.turns = []


def _send_message(api_url: str, message: str) -> None:
    history = history_from_turns(st.session_state.turns)
    payload = build_chat_payload(message, st.session_state.session_id, history)
    st.session_state.turns.append({"role": "user", "content": message})

    result = post_chat(api_url, payload)
    if not result["ok"]:
        st.session_state.turns.append(
            {
                "role": "assistant",
                "content": result["error"],
                "sources": [],
                "tool_trace": [],
                "confirmation": None,
                "error": result["error"],
                "confirmation_status": None,
            }
        )
        return

    body = result["body"] or {}
    confirmation = body.get("confirmation")
    st.session_state.turns.append(
        {
            "role": "assistant",
            "content": empty_answer_fallback(body.get("answer"), body.get("error")),
            "sources": body.get("sources") or [],
            "tool_trace": body.get("tool_trace") or [],
            "confirmation": confirmation,
            "error": body.get("error"),
            "confirmation_status": None,
        }
    )


def _render_confirmation(turn: dict[str, Any], index: int) -> None:
    confirmation = turn.get("confirmation") or {}
    status = turn.get("confirmation_status")
    headline = confirmation_headline(confirmation)

    st.warning("Confirmation required — this action has not been executed.")
    st.markdown(f"**Proposed action:** `{confirmation.get('action_type', '')}`")
    if confirmation.get("summary"):
        st.write(confirmation["summary"])
    payload = confirmation.get("payload") or {}
    if payload:
        st.write("What will happen if confirmed (not executed by this UI):")
        st.json(payload)
    if confirmation.get("sources"):
        st.caption("Sources: " + ", ".join(confirmation["sources"]))

    if status == "confirmed":
        st.info("Staff confirmed the proposal. No state-changing action was executed.")
        return
    if status == "cancelled":
        st.info("Staff cancelled the proposal. Nothing was executed.")
        return

    col_confirm, col_cancel = st.columns(2)
    if col_confirm.button("Confirm", key=f"confirm_{index}", type="primary"):
        turn["confirmation_status"] = "confirmed"
        st.rerun()
    if col_cancel.button("Cancel", key=f"cancel_{index}"):
        turn["confirmation_status"] = "cancelled"
        st.rerun()
    if headline:
        st.caption(headline)


def _render_turn(turn: dict[str, Any], index: int, show_tool_trace: bool) -> None:
    with st.chat_message(turn["role"]):
        st.write(turn.get("content") or "")
        if turn.get("error") and turn["role"] == "assistant":
            st.error(turn["error"])
        sources = turn.get("sources") or []
        if sources:
            st.markdown("**Sources**")
            for source in sources:
                st.markdown(f"- `{source}`")
        if confirmation_is_pending(turn) or turn.get("confirmation"):
            _render_confirmation(turn, index)
        if show_tool_trace and turn.get("tool_trace"):
            with st.expander("Tool trace"):
                st.json(turn["tool_trace"])


def main() -> None:
    st.set_page_config(page_title="ParcelPilot Support", layout="centered")
    _init_state()

    st.title("ParcelPilot Support")
    st.caption("Internal operations assistant. Actions that change state require confirmation and are not auto-executed.")

    with st.sidebar:
        st.subheader("Session")
        api_url = st.text_input(
            "API URL",
            value=os.getenv("PARCELPILOT_API_URL", DEFAULT_API_URL),
        )
        st.caption(f"Session ID: `{st.session_state.session_id}`")
        st.session_state.show_tool_trace = st.checkbox(
            "Show tool trace",
            value=st.session_state.show_tool_trace,
        )
        if st.button("Clear conversation"):
            _clear_conversation()
            st.rerun()

    for index, turn in enumerate(st.session_state.turns):
        _render_turn(turn, index, st.session_state.show_tool_trace)

    prompt = st.chat_input("Message")
    if prompt and prompt.strip():
        _send_message(api_url.strip() or DEFAULT_API_URL, prompt.strip())
        st.rerun()


if __name__ == "__main__":
    main()
