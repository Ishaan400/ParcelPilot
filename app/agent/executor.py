"""Execute agent tools via ParcelPilotTools and ParcelPilotActions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.actions.service import ParcelPilotActions
from app.agent.errors import redact_public_error
from app.agent.models import ConfirmationRequest
from app.tools.tools import ParcelPilotTools

DATETIME_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M")


def parse_optional_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(text)


def serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [serialize(item) for item in value]
    return value


def is_deprecated_policy(filename: str) -> bool:
    name = filename.casefold()
    return "deprecated" in name or "support_policy_v2" in name


def collect_sources(payload: Any, bucket: list[str]) -> None:
    if isinstance(payload, dict):
        filename = payload.get("source_filename")
        if (
            isinstance(filename, str)
            and filename not in bucket
            and not is_deprecated_policy(filename)
        ):
            bucket.append(filename)
        sources = payload.get("sources")
        if isinstance(sources, list):
            for item in sources:
                if (
                    isinstance(item, str)
                    and item not in bucket
                    and not is_deprecated_policy(item)
                ):
                    bucket.append(item)
        for nested in payload.values():
            collect_sources(nested, bucket)
    elif isinstance(payload, list):
        for item in payload:
            collect_sources(item, bucket)


class ToolExecutor:
    def __init__(self, tools: ParcelPilotTools, actions: ParcelPilotActions) -> None:
        self.tools = tools
        self.actions = actions
        self.confirmation: ConfirmationRequest | None = None
        self.sources: list[str] = []

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self._dispatch(name, arguments)
        except Exception as exc:  # noqa: BLE001 - surface tool failures to the model
            return {"ok": False, "error": redact_public_error(str(exc)) or str(exc), "tool": name}

        collect_sources(result, self.sources)
        return result

    def _dispatch(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "get_account":
            record = self.tools.get_account(arguments["account_id"])
            return {"found": record is not None, "account": serialize(record)}
        if name == "get_account_by_name":
            record = self.tools.get_account_by_name(arguments["account_name"])
            return {"found": record is not None, "account": serialize(record)}
        if name == "list_accounts":
            return {"accounts": serialize(self.tools.list_accounts())}
        if name == "get_order":
            record = self.tools.get_order(arguments["order_id"])
            return {"found": record is not None, "order": serialize(record)}
        if name == "list_orders":
            return {"orders": serialize(self.tools.list_orders(arguments.get("account_id")))}
        if name == "get_ticket":
            record = self.tools.get_ticket(arguments["ticket_id"])
            return {"found": record is not None, "ticket": serialize(record)}
        if name == "list_tickets":
            return {
                "tickets": serialize(
                    self.tools.list_tickets(
                        account_id=arguments.get("account_id"),
                        status=arguments.get("status"),
                    )
                )
            }
        if name == "search_documents":
            top_k = int(arguments.get("top_k") or 5)
            hits = serialize(self.tools.search_documents(arguments["query"], top_k=top_k))
            annotated: list[dict[str, Any]] = []
            excluded_deprecated = False
            for hit in hits:
                item = dict(hit)
                filename = str(item.get("source_filename") or "")
                if is_deprecated_policy(filename):
                    excluded_deprecated = True
                    continue
                item["is_current_policy"] = True
                annotated.append(item)
            payload: dict[str, Any] = {"results": annotated}
            if excluded_deprecated:
                payload["deprecated_policy_excluded"] = True
            return payload
        if name == "evaluate_cancellation":
            return serialize(
                self.actions.evaluate_cancellation(
                    arguments["order_id"],
                    requested_at=parse_optional_datetime(arguments.get("requested_at")),
                )
            )
        if name == "evaluate_service_credit":
            return serialize(
                self.actions.evaluate_service_credit(
                    arguments["order_id"],
                    as_of=parse_optional_datetime(arguments.get("as_of")),
                )
            )
        if name == "get_first_response_target":
            return serialize(
                self.actions.get_first_response_target(
                    arguments["account_id"],
                    arguments["severity"],
                )
            )
        if name == "evaluate_bulk_upload":
            return serialize(
                self.actions.evaluate_bulk_upload(
                    arguments["account_id"],
                    csv_row_count=arguments.get("csv_row_count"),
                )
            )
        if name == "interpret_pickup_status":
            return serialize(self.actions.interpret_pickup_status(arguments["order_id"]))
        if name == "request_action_confirmation":
            payload = dict(arguments.get("payload") or {})
            if arguments.get("order_id"):
                payload.setdefault("order_id", arguments["order_id"])
            if arguments.get("account_id"):
                payload.setdefault("account_id", arguments["account_id"])
            self.confirmation = ConfirmationRequest(
                action_type=arguments["action_type"],
                summary=arguments["summary"],
                payload=payload,
                sources=list(arguments.get("sources") or []),
                requires_user_confirmation=True,
                executed=False,
            )
            collect_sources({"sources": self.confirmation.sources}, self.sources)
            return {
                "queued": True,
                "executed": False,
                "confirmation": serialize(self.confirmation),
            }
        return {"ok": False, "error": f"Unknown tool: {name}", "tool": name}
