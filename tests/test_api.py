from fastapi.testclient import TestClient

from app.agent.models import AgentResponse, ConfirmationRequest, ToolTrace
from app.api.deps import get_agent
from app.api.main import app


class FakeAgent:
    def __init__(self, response: AgentResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, list | None]] = []

    def run(self, user_message: str, history: list | None = None) -> AgentResponse:
        self.calls.append((user_message, history))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def _client(fake: FakeAgent) -> TestClient:
    app.dependency_overrides[get_agent] = lambda: fake
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_rejects_empty_message() -> None:
    fake = FakeAgent(AgentResponse(answer="unused"))
    client = _client(fake)
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422
    assert fake.calls == []


def test_normal_chat_request() -> None:
    fake = FakeAgent(AgentResponse(answer="Hello from ParcelPilot."))
    client = _client(fake)
    response = client.post(
        "/chat",
        json={"message": "Hello", "session_id": "sess-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Hello from ParcelPilot."
    assert body["session_id"] == "sess-1"
    assert body["error"] is None
    assert body["confirmation"] is None
    assert fake.calls == [("Hello", None)]
    assert "GROQ_API_KEY" not in str(body)
    assert "sk-" not in str(body)


def test_document_retrieval_response() -> None:
    fake = FakeAgent(
        AgentResponse(
            answer="KI-208 causes intermittent Bulk Upload failures above about 3,000 rows.",
            sources=["04_Product_Operations_Guide_and_Known_Issues.pdf"],
            tool_trace=[
                ToolTrace(
                    name="search_documents",
                    arguments={"query": "KI-208"},
                    result={"results": [{"source_filename": "04_Product_Operations_Guide_and_Known_Issues.pdf"}]},
                )
            ],
        )
    )
    client = _client(fake)
    response = client.post("/chat", json={"message": "What is KI-208?"})
    assert response.status_code == 200
    body = response.json()
    assert "KI-208" in body["answer"]
    assert body["sources"] == ["04_Product_Operations_Guide_and_Known_Issues.pdf"]
    assert body["tool_trace"][0]["name"] == "search_documents"


def test_structured_data_response() -> None:
    fake = FakeAgent(
        AgentResponse(
            answer="Northstar Logistics is ACCT-001 on the Enterprise plan.",
            tool_trace=[
                ToolTrace(
                    name="get_account",
                    arguments={"account_id": "ACCT-001"},
                    result={"found": True, "account": {"account_name": "Northstar Logistics"}},
                )
            ],
        )
    )
    client = _client(fake)
    response = client.post("/chat", json={"message": "What plan is ACCT-001 on?"})
    assert response.status_code == 200
    body = response.json()
    assert "Enterprise" in body["answer"]
    assert body["tool_trace"][0]["result"]["found"] is True


def test_confirmation_required_response() -> None:
    fake = FakeAgent(
        AgentResponse(
            answer="Recommended: cancel ORD-1001. Waiting for confirmation; not executed.",
            sources=["05_Northstar_Logistics_Enterprise_Agreement.pdf"],
            confirmation=ConfirmationRequest(
                action_type="cancel_shipment",
                summary="Cancel ORD-1001 with no fee pending human confirmation.",
                payload={"order_id": "ORD-1001"},
                sources=["05_Northstar_Logistics_Enterprise_Agreement.pdf"],
                requires_user_confirmation=True,
                executed=False,
            ),
        )
    )
    client = _client(fake)
    response = client.post("/chat", json={"message": "Please cancel ORD-1001."})
    assert response.status_code == 200
    body = response.json()
    confirmation = body["confirmation"]
    assert confirmation["action_type"] == "cancel_shipment"
    assert confirmation["executed"] is False
    assert confirmation["requires_user_confirmation"] is True
    assert confirmation["payload"]["order_id"] == "ORD-1001"


def test_agent_error_is_returned_without_api_key() -> None:
    fake = FakeAgent(
        AgentResponse(
            answer="I could not complete the request because the language-model API call failed.",
            error="api timeout",
        )
    )
    client = _client(fake)
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["error"] == "api timeout"
    assert "language-model" in body["answer"]
    assert "GROQ_API_KEY" not in str(body)


def test_unexpected_agent_exception_is_http_500() -> None:
    fake = FakeAgent(error=RuntimeError("openai api_key leaked-secret"))
    client = _client(fake)
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "leaked-secret" not in detail
    assert "api_key" not in detail.casefold()


def test_chat_response_redacts_api_key_in_agent_error() -> None:
    fake = FakeAgent(
        AgentResponse(
            answer="I could not complete the request because the language-model API call failed.",
            error="Incorrect API key provided: sk-test-abc123XYZ",
        )
    )
    client = _client(fake)
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    body = response.json()
    assert "sk-test-abc123XYZ" not in str(body)
    assert "sk-test" not in str(body)
    assert body["error"] == "language_model_error"
