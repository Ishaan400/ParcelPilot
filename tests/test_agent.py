import json
from types import SimpleNamespace

import pytest

from app.actions.service import ParcelPilotActions
from app.agent.agent import SupportAgent
from app.agent.openai_tools import OPENAI_TOOLS
from app.agent.prompts import SYSTEM_PROMPT
from app.tools.tools import ParcelPilotTools


def _tool_response(calls: list[tuple[str, dict]]) -> SimpleNamespace:
    tool_calls = []
    for index, (name, arguments) in enumerate(calls):
        tool_calls.append(
            SimpleNamespace(
                id=f"call_{index}",
                type="function",
                function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
            )
        )
    message = SimpleNamespace(content=None, tool_calls=tool_calls, role="assistant")
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="tool_calls")])


def _text_response(content: str) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=None, role="assistant")
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])


class FakeOpenAI:
    def __init__(self, script: list[SimpleNamespace]) -> None:
        self._script = list(script)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._script:
            raise RuntimeError("No scripted OpenAI responses remaining")
        return self._script.pop(0)


@pytest.fixture(scope="module")
def shared_tools() -> ParcelPilotTools:
    return ParcelPilotTools()


@pytest.fixture(scope="module")
def shared_actions(shared_tools: ParcelPilotTools) -> ParcelPilotActions:
    return ParcelPilotActions(shared_tools)


def _agent(script, shared_tools, shared_actions) -> tuple[SupportAgent, FakeOpenAI]:
    client = FakeOpenAI(script)
    agent = SupportAgent(
        tools=shared_tools,
        actions=shared_actions,
        client=client,
        max_turns=6,
    )
    return agent, client


def test_system_prompt_sets_precedence_without_fee_rules() -> None:
    assert "signed customer agreement" in SYSTEM_PROMPT.lower()
    assert "support policy v3" in SYSTEM_PROMPT.lower()
    assert "deprecated" in SYSTEM_PROMPT.lower()
    assert "historical tickets" in SYSTEM_PROMPT.lower()
    assert "INR 250" not in SYSTEM_PROMPT
    assert "30 minutes" not in SYSTEM_PROMPT


def test_openai_tool_schemas_cover_lookups_actions_and_confirmation() -> None:
    names = {item["function"]["name"] for item in OPENAI_TOOLS}
    assert {
        "get_account",
        "get_order",
        "get_ticket",
        "search_documents",
        "evaluate_cancellation",
        "request_action_confirmation",
    } <= names


def test_evaluate_cancellation_schema_allows_null_requested_at() -> None:
    schema = next(
        item["function"]["parameters"]
        for item in OPENAI_TOOLS
        if item["function"]["name"] == "evaluate_cancellation"
    )
    requested_at = schema["properties"]["requested_at"]["type"]
    assert "null" in requested_at if isinstance(requested_at, list) else requested_at == "null"
    assert "string" in requested_at
    assert "requested_at" not in schema["required"]


def test_evaluate_cancellation_accepts_null_requested_at(shared_tools, shared_actions) -> None:
    from app.agent.executor import ToolExecutor

    executor = ToolExecutor(shared_tools, shared_actions)
    result = executor.execute(
        "evaluate_cancellation",
        {"order_id": "ORD-2001", "requested_at": None},
    )
    assert result.get("error") is None
    assert result["order_id"] == "ORD-2001"
    assert result["status"] in {"ok", "needs_verification"}


def test_evaluate_bulk_upload_schema_allows_null_csv_row_count() -> None:
    schema = next(
        item["function"]["parameters"]
        for item in OPENAI_TOOLS
        if item["function"]["name"] == "evaluate_bulk_upload"
    )
    csv_row_count = schema["properties"]["csv_row_count"]["type"]
    assert "null" in csv_row_count if isinstance(csv_row_count, list) else csv_row_count == "null"
    assert "integer" in csv_row_count
    assert schema["required"] == ["account_id"]
    assert "csv_row_count" not in schema["required"]


def test_evaluate_bulk_upload_accepts_null_csv_row_count(shared_tools, shared_actions) -> None:
    from app.agent.executor import ToolExecutor

    executor = ToolExecutor(shared_tools, shared_actions)
    result = executor.execute(
        "evaluate_bulk_upload",
        {"account_id": "ACCT-002", "csv_row_count": None},
    )
    assert result.get("error") is None
    assert result["account_id"] == "ACCT-002"
    assert result["status"] == "ok"
    assert result["bulk_upload_included"] is True
    assert result["csv_row_count"] is None
    assert result["supported_row_limit"] == 5000


def test_evaluate_bulk_upload_integer_row_count_unchanged(shared_tools, shared_actions) -> None:
    from app.agent.executor import ToolExecutor

    executor = ToolExecutor(shared_tools, shared_actions)
    result = executor.execute(
        "evaluate_bulk_upload",
        {"account_id": "ACCT-002", "csv_row_count": 4200},
    )
    assert result.get("error") is None
    assert result["status"] == "ok"
    assert result["bulk_upload_included"] is True
    assert result["csv_row_count"] == 4200
    assert result["within_supported_limit"] is True
    assert result["known_issue_ki208"] is True
    assert result["workaround"] is not None


def test_simple_document_question(shared_tools, shared_actions) -> None:
    agent, client = _agent(
        [
            _tool_response([("search_documents", {"query": "KI-208 bulk upload"})]),
            _text_response(
                "KI-208 causes intermittent Bulk Upload failures above about 3,000 rows. "
                "Source: 04_Product_Operations_Guide_and_Known_Issues.pdf"
            ),
        ],
        shared_tools,
        shared_actions,
    )
    result = agent.run("What is KI-208?")
    assert result.error is None
    assert "KI-208" in result.answer
    assert result.tool_trace[0].name == "search_documents"
    assert "04_Product_Operations_Guide_and_Known_Issues.pdf" in result.sources
    assert client.calls[0]["tools"] == OPENAI_TOOLS


def test_structured_data_question(shared_tools, shared_actions) -> None:
    agent, _client = _agent(
        [
            _tool_response([("get_account", {"account_id": "ACCT-001"})]),
            _text_response("Northstar Logistics is ACCT-001 on the Enterprise plan."),
        ],
        shared_tools,
        shared_actions,
    )
    result = agent.run("What plan is ACCT-001 on?")
    assert result.tool_trace[0].result["found"] is True
    assert result.tool_trace[0].result["account"]["account_name"] == "Northstar Logistics"
    assert "Enterprise" in result.answer


def test_multi_step_order_account_question(shared_tools, shared_actions) -> None:
    agent, _client = _agent(
        [
            _tool_response([("get_order", {"order_id": "ORD-1001"})]),
            _tool_response([("get_account", {"account_id": "ACCT-001"})]),
            _tool_response(
                [("search_documents", {"query": "Northstar cancellation BOOKED"})]
            ),
            _text_response(
                "ORD-1001 belongs to Northstar Logistics (ACCT-001). "
                "Sources: 05_Northstar_Logistics_Enterprise_Agreement.pdf"
            ),
        ],
        shared_tools,
        shared_actions,
    )
    result = agent.run("Who owns ORD-1001 and what cancellation terms apply?")
    names = [item.name for item in result.tool_trace]
    assert names[:3] == ["get_order", "get_account", "search_documents"]
    assert result.tool_trace[0].result["order"]["account_id"] == "ACCT-001"
    assert result.tool_trace[1].result["account"]["account_id"] == "ACCT-001"
    assert "05_Northstar_Logistics_Enterprise_Agreement.pdf" in result.sources


def test_action_business_rule_question(shared_tools, shared_actions) -> None:
    agent, _client = _agent(
        [
            _tool_response([("evaluate_cancellation", {"order_id": "ORD-1001"})]),
            _text_response(
                "ORD-1001 may be cancelled with no fee under the Northstar agreement."
            ),
        ],
        shared_tools,
        shared_actions,
    )
    result = agent.run("Can we cancel ORD-1001 and is there a fee?")
    decision = result.tool_trace[0].result
    assert decision["can_cancel"] is True
    assert decision["cancellation_fee_inr"] == 0
    assert "05_Northstar_Logistics_Enterprise_Agreement.pdf" in result.sources
    assert "no fee" in result.answer.lower()


def test_missing_record(shared_tools, shared_actions) -> None:
    agent, _client = _agent(
        [
            _tool_response([("get_order", {"order_id": "ORD-9999"})]),
            _text_response("Order ORD-9999 was not found in the dataset."),
        ],
        shared_tools,
        shared_actions,
    )
    result = agent.run("What is the status of ORD-9999?")
    assert result.tool_trace[0].result["found"] is False
    assert result.tool_trace[0].result["order"] is None
    assert "not found" in result.answer.lower()


def test_insufficient_evidence(shared_tools, shared_actions) -> None:
    agent, _client = _agent(
        [
            _tool_response([("evaluate_service_credit", {"order_id": "ORD-1001"})]),
            _text_response(
                "There is insufficient evidence to treat this as a missed pickup. "
                "Status is BOOKED on SwiftShip, so KI-211 requires carrier verification."
            ),
        ],
        shared_tools,
        shared_actions,
    )
    result = agent.run("Is ORD-1001 eligible for a failed-pickup credit?")
    decision = result.tool_trace[0].result
    assert decision["status"] == "needs_verification"
    assert decision["eligible"] is False
    assert "insufficient" in result.answer.lower() or "verification" in result.answer.lower()


def test_tool_failure(shared_tools, shared_actions) -> None:
    class FailingTools:
        def get_account(self, account_id: str):
            raise RuntimeError("account lookup unavailable")

    agent, _client = _agent(
        [
            _tool_response([("get_account", {"account_id": "ACCT-001"})]),
            _text_response(
                "I could not look up ACCT-001 because the account tool failed."
            ),
        ],
        FailingTools(),
        shared_actions,
    )
    result = agent.run("What is the plan for ACCT-001?")
    assert result.tool_trace[0].error == "account lookup unavailable"
    assert result.tool_trace[0].result["ok"] is False
    assert "failed" in result.answer.lower()


def test_confirmation_required_action(shared_tools, shared_actions) -> None:
    agent, _client = _agent(
        [
            _tool_response([("evaluate_cancellation", {"order_id": "ORD-1001"})]),
            _tool_response(
                [
                    (
                        "request_action_confirmation",
                        {
                            "action_type": "cancel_shipment",
                            "summary": "Cancel ORD-1001 with no fee pending human confirmation.",
                            "order_id": "ORD-1001",
                            "account_id": "ACCT-001",
                            "sources": ["05_Northstar_Logistics_Enterprise_Agreement.pdf"],
                        },
                    )
                ]
            ),
            _text_response(
                "Recommended: cancel ORD-1001 with no fee. Waiting for confirmation; not executed."
            ),
        ],
        shared_tools,
        shared_actions,
    )
    result = agent.run("Please cancel ORD-1001.")
    assert result.confirmation is not None
    assert result.confirmation.action_type == "cancel_shipment"
    assert result.confirmation.executed is False
    assert result.confirmation.requires_user_confirmation is True
    assert result.confirmation.payload["order_id"] == "ORD-1001"
    assert "not executed" in result.answer.lower()


def test_deprecated_policy_search_is_not_returned_to_the_agent(shared_tools, shared_actions) -> None:
    from app.retrieval.loader import DEFAULT_DOCUMENTS_DIR

    assert (DEFAULT_DOCUMENTS_DIR / "02_Support_Policy_v2_DEPRECATED.pdf").is_file()
    agent, _client = _agent(
        [
            _tool_response(
                [("search_documents", {"query": "DEPRECATED Support Policy v2 P1 Enterprise"})]
            ),
            _text_response(
                "Support Policy v2 is deprecated and is not used as current policy. "
                "Use Support Policy v3."
            ),
        ],
        shared_tools,
        shared_actions,
    )
    result = agent.run("What are the current P1 targets from Support Policy v2?")
    hits = result.tool_trace[0].result["results"]
    assert all("DEPRECATED" not in hit.get("source_filename", "") for hit in hits)
    assert all(hit.get("is_current_policy") is True for hit in hits)
    assert all("DEPRECATED" not in source for source in result.sources)
    assert "deprecated" in result.answer.lower()


def test_executor_strips_v2_even_if_tools_return_it(shared_actions) -> None:
    from app.agent.executor import ToolExecutor
    from app.retrieval.models import RetrievalResult

    class InjectingTools:
        def search_documents(self, query: str, top_k: int = 5):
            return [
                RetrievalResult(
                    text="Enterprise P1 1 hour",
                    source_filename="02_Support_Policy_v2_DEPRECATED.pdf",
                    title="ParcelPilot Support Policy v2",
                    chunk_id="02:0",
                    chunk_index=0,
                    score=99.0,
                    metadata={"Status": "DEPRECATED"},
                ),
                RetrievalResult(
                    text="Enterprise P1 30 minutes, 24x7",
                    source_filename="01_Support_Policy_v3_CURRENT.pdf",
                    title="ParcelPilot Support Policy v3",
                    chunk_id="01:0",
                    chunk_index=0,
                    score=50.0,
                    metadata={"Status": "CURRENT"},
                ),
            ]

    executor = ToolExecutor(InjectingTools(), shared_actions)
    payload = executor.execute("search_documents", {"query": "Enterprise P1"})
    filenames = [hit["source_filename"] for hit in payload["results"]]
    assert "02_Support_Policy_v2_DEPRECATED.pdf" not in filenames
    assert "01_Support_Policy_v3_CURRENT.pdf" in filenames
    assert payload.get("deprecated_policy_excluded") is True
    assert all("DEPRECATED" not in source for source in executor.sources)


def test_ambiguous_request_asks_for_identifier(shared_tools, shared_actions) -> None:
    agent, _client = _agent(
        [
            _text_response(
                "The request is ambiguous. Please provide an order_id or account name."
            ),
        ],
        shared_tools,
        shared_actions,
    )
    result = agent.run("Can we cancel the shipment?")
    assert result.tool_trace == []
    assert result.confirmation is None
    assert "ambiguous" in result.answer.lower()


def test_api_error_is_graceful(shared_tools, shared_actions) -> None:
    class BrokenClient:
        chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("api timeout"))
            )
        )

    agent = SupportAgent(
        tools=shared_tools,
        actions=shared_actions,
        client=BrokenClient(),
    )
    result = agent.run("Hello")
    assert result.error == "api timeout"
    assert "language-model" in result.answer


def test_api_key_is_not_returned_in_agent_error(shared_tools, shared_actions) -> None:
    leaked = "Incorrect API key provided: sk-test-abc123XYZ"

    class LeakyClient:
        chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: (_ for _ in ()).throw(RuntimeError(leaked))
            )
        )

    agent = SupportAgent(
        tools=shared_tools,
        actions=shared_actions,
        client=LeakyClient(),
    )
    result = agent.run("Hello")
    dumped = str(result.model_dump())
    assert "sk-test-abc123XYZ" not in dumped
    assert "api key" not in (result.error or "").casefold()
    assert result.error == "language_model_error"
    assert "language-model" in result.answer


def test_default_client_is_configured_for_groq(monkeypatch, shared_tools, shared_actions) -> None:
    import sys
    import types

    from app.agent import agent as agent_module
    from app.config.settings import GROQ_BASE_URL

    captured: dict[str, object] = {}

    class FakeSDKClient:
        def __init__(self, api_key=None, base_url=None) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url

        def __repr__(self) -> str:
            return "FakeSDKClient(api_key=REDACTED, base_url=%r)" % captured.get("base_url")

    fake_mod = types.ModuleType("openai")
    fake_mod.OpenAI = FakeSDKClient
    monkeypatch.setitem(sys.modules, "openai", fake_mod)
    monkeypatch.setattr(agent_module, "GROQ_API_KEY", "gsk-test-placeholder-not-a-real-key")
    monkeypatch.setattr(agent_module, "GROQ_MODEL", "openai/gpt-oss-120b")

    agent = SupportAgent(tools=shared_tools, actions=shared_actions, client=None)
    client = agent._openai()

    assert agent.model == "openai/gpt-oss-120b"
    assert captured["base_url"] == GROQ_BASE_URL
    assert captured["api_key"] == "gsk-test-placeholder-not-a-real-key"
    dump = repr(client)
    assert "gsk-test-placeholder-not-a-real-key" not in dump
    assert "GROQ_API_KEY" not in dump
