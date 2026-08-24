from app.ui.client import (
    build_chat_payload,
    confirmation_headline,
    confirmation_is_pending,
    empty_answer_fallback,
    format_api_failure,
    history_from_turns,
    post_chat,
)


def test_build_chat_payload_includes_optional_fields() -> None:
    payload = build_chat_payload(
        "Hello",
        "sess-1",
        [{"role": "user", "content": "prior"}],
    )
    assert payload == {
        "message": "Hello",
        "session_id": "sess-1",
        "history": [{"role": "user", "content": "prior"}],
    }


def test_history_from_turns_skips_empty_and_non_chat_roles() -> None:
    history = history_from_turns(
        [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
            {"role": "assistant", "content": "   "},
            {"role": "system", "content": "nope"},
        ]
    )
    assert history == [
        {"role": "user", "content": "Q"},
        {"role": "assistant", "content": "A"},
    ]


def test_confirmation_pending_until_staff_decides() -> None:
    turn = {"confirmation": {"action_type": "cancel_shipment"}, "confirmation_status": None}
    assert confirmation_is_pending(turn) is True
    turn["confirmation_status"] = "confirmed"
    assert confirmation_is_pending(turn) is False


def test_confirmation_headline() -> None:
    text = confirmation_headline(
        {"action_type": "cancel_shipment", "summary": "Cancel ORD-1001"}
    )
    assert text.startswith("cancel_shipment")
    assert "ORD-1001" in text


def test_empty_answer_fallback() -> None:
    assert empty_answer_fallback("  ", None) == "The agent returned an empty response."
    assert empty_answer_fallback("", "api timeout") == "The agent reported an error."
    assert empty_answer_fallback("OK", None) == "OK"


def test_format_api_failure() -> None:
    assert "unavailable" in format_api_failure(None, None).casefold()
    assert "invalid" in format_api_failure(422, "empty").casefold()
    assert "500" in format_api_failure(500, "boom")


def test_post_chat_success(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200
        is_success = True

        def json(self):
            return {"answer": "hi", "sources": [], "error": None}

    def fake_post(url, json, timeout):
        assert url.endswith("/chat")
        assert json["message"] == "Hello"
        return FakeResponse()

    monkeypatch.setattr("app.ui.client.httpx.post", fake_post)
    result = post_chat("http://127.0.0.1:8000", {"message": "Hello"})
    assert result["ok"] is True
    assert result["body"]["answer"] == "hi"


def test_post_chat_unavailable(monkeypatch) -> None:
    import httpx

    def raise_request_error(url, json, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr("app.ui.client.httpx.post", raise_request_error)
    result = post_chat("http://127.0.0.1:8000", {"message": "Hello"})
    assert result["ok"] is False
    assert result["status_code"] is None
    assert "unavailable" in result["error"].casefold()
