from app.data.models import AccountPlan, OrderStatus, TicketStatus
from app.tools.tools import ParcelPilotTools


def test_get_account_success() -> None:
    tools = ParcelPilotTools()
    account = tools.get_account("ACCT-001")
    assert account is not None
    assert account.account_id == "ACCT-001"
    assert account.account_name == "Northstar Logistics"
    assert account.plan == AccountPlan.ENTERPRISE


def test_get_account_by_name() -> None:
    tools = ParcelPilotTools()
    account = tools.get_account_by_name("LumenWorks")
    assert account is not None
    assert account.account_id == "ACCT-002"


def test_list_accounts() -> None:
    tools = ParcelPilotTools()
    accounts = tools.list_accounts()
    assert len(accounts) == 4
    assert {account.account_id for account in accounts} == {
        "ACCT-001",
        "ACCT-002",
        "ACCT-003",
        "ACCT-004",
    }


def test_get_order_success() -> None:
    tools = ParcelPilotTools()
    order = tools.get_order("ORD-1001")
    assert order is not None
    assert order.account_id == "ACCT-001"
    assert order.status == OrderStatus.BOOKED


def test_get_ticket_success() -> None:
    tools = ParcelPilotTools()
    ticket = tools.get_ticket("TKT-501")
    assert ticket is not None
    assert ticket.account_id == "ACCT-001"
    assert ticket.status == TicketStatus.OPEN


def test_list_orders_filtered_by_account() -> None:
    tools = ParcelPilotTools()
    orders = tools.list_orders(account_id="ACCT-001")
    assert orders
    assert {order.order_id for order in orders} == {"ORD-1001", "ORD-1002"}
    assert all(order.account_id == "ACCT-001" for order in orders)


def test_list_tickets_filtered_by_account_and_status() -> None:
    tools = ParcelPilotTools()
    tickets = tools.list_tickets(account_id="ACCT-001", status="open")
    assert tickets
    assert all(ticket.account_id == "ACCT-001" for ticket in tickets)
    assert all(ticket.status == TicketStatus.OPEN for ticket in tickets)


def test_search_documents() -> None:
    tools = ParcelPilotTools()
    results = tools.search_documents("KI-208 bulk upload CSV")
    assert results
    top = results[0]
    assert top.source_filename == "04_Product_Operations_Guide_and_Known_Issues.pdf"
    assert "KI-208" in top.text
    assert top.chunk_id
    assert isinstance(top.score, float)


def test_not_found_lookups_return_none() -> None:
    tools = ParcelPilotTools()
    assert tools.get_account("ACCT-999") is None
    assert tools.get_account_by_name("Unknown Customer") is None
    assert tools.get_order("ORD-9999") is None
    assert tools.get_ticket("TKT-999") is None


def test_filtered_lists_empty_when_no_match() -> None:
    tools = ParcelPilotTools()
    assert tools.list_orders(account_id="ACCT-999") == []
    assert tools.list_tickets(account_id="ACCT-999") == []
    assert tools.search_documents("   ") == []


def test_search_documents_excludes_deprecated_policy() -> None:
    from app.retrieval.loader import DEFAULT_DOCUMENTS_DIR

    assert (DEFAULT_DOCUMENTS_DIR / "02_Support_Policy_v2_DEPRECATED.pdf").is_file()
    tools = ParcelPilotTools()
    results = tools.search_documents("DEPRECATED Support Policy v2 Enterprise P1")
    assert all("DEPRECATED" not in hit.source_filename for hit in results)
    assert all("v2" not in hit.source_filename.casefold() for hit in results)
