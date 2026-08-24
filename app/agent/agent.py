"""ParcelPilot support agent orchestration with Groq (OpenAI-compatible) tool calling."""

from __future__ import annotations

import json
from typing import Any

from app.actions.service import ParcelPilotActions
from app.agent.errors import (
    PUBLIC_CLIENT_CREATE_ANSWER,
    PUBLIC_LLM_ANSWER,
    log_and_redact,
    redact_public_error,
)
from app.agent.executor import ToolExecutor
from app.agent.models import AgentResponse, ToolTrace
from app.agent.openai_tools import OPENAI_TOOLS
from app.agent.prompts import SYSTEM_PROMPT
from app.config.settings import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL
from app.tools.tools import ParcelPilotTools


class SupportAgent:
    def __init__(
        self,
        tools: ParcelPilotTools | None = None,
        actions: ParcelPilotActions | None = None,
        client: Any | None = None,
        model: str | None = None,
        max_turns: int = 8,
    ) -> None:
        self.tools = tools or ParcelPilotTools()
        self.actions = actions or ParcelPilotActions(self.tools)
        self.client = client
        self.model = model or GROQ_MODEL
        self.max_turns = max_turns

    def _openai(self) -> Any:
        if self.client is not None:
            return self.client
        from openai import OpenAI

        return OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

    def run(self, user_message: str, history: list[dict[str, Any]] | None = None) -> AgentResponse:
        executor = ToolExecutor(self.tools, self.actions)
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        trace: list[ToolTrace] = []

        try:
            client = self._openai()
        except Exception as exc:  # noqa: BLE001
            return AgentResponse(
                answer=PUBLIC_CLIENT_CREATE_ANSWER,
                error=log_and_redact(exc),
            )

        for _ in range(self.max_turns):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=OPENAI_TOOLS,
                    tool_choice="auto",
                )
            except Exception as exc:  # noqa: BLE001
                return AgentResponse(
                    answer=PUBLIC_LLM_ANSWER,
                    sources=list(executor.sources),
                    confirmation=executor.confirmation,
                    tool_trace=trace,
                    error=log_and_redact(exc),
                )

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                answer = (getattr(message, "content", None) or "").strip()
                if not answer:
                    answer = "I did not receive a usable answer from the model."
                return AgentResponse(
                    answer=answer,
                    sources=list(executor.sources),
                    confirmation=executor.confirmation,
                    tool_trace=trace,
                )

            assistant_tool_calls: list[dict[str, Any]] = []
            tool_results: list[dict[str, Any]] = []
            for call in tool_calls:
                function = call.function
                raw_arguments = function.arguments or "{}"
                try:
                    arguments = json.loads(raw_arguments) if raw_arguments else {}
                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be a JSON object.")
                    result = executor.execute(function.name, arguments)
                    raw_error = result.get("error") if isinstance(result, dict) else None
                    error = redact_public_error(raw_error) if isinstance(raw_error, str) else raw_error
                    if isinstance(result, dict) and isinstance(result.get("error"), str):
                        result = {**result, "error": error}
                except (json.JSONDecodeError, ValueError) as exc:
                    arguments = {}
                    result = {
                        "ok": False,
                        "error": f"Invalid tool arguments: {exc}",
                        "tool": function.name,
                    }
                    error = result["error"]

                trace.append(
                    ToolTrace(
                        name=function.name,
                        arguments=arguments,
                        result=result,
                        error=error,
                    )
                )
                assistant_tool_calls.append(
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": function.name, "arguments": raw_arguments},
                    }
                )
                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result),
                    }
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": getattr(message, "content", None),
                    "tool_calls": assistant_tool_calls,
                }
            )
            messages.extend(tool_results)

        return AgentResponse(
            answer=(
                "I stopped because the tool-call limit was reached before a final "
                "answer was produced. Please retry with a more specific question."
            ),
            sources=list(executor.sources),
            confirmation=executor.confirmation,
            tool_trace=trace,
            error="max_turns_exceeded",
        )
