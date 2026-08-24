from datetime import datetime

from app.data.models import AccountPlan, AccountStatus, OrderStatus, TicketStatus
from app.data.repository import DEFAULT_WORKBOOK_PATH, ParcelPilotRepository


def test_workbook_path_exists() -> None:
    assert DEFAULT_WORKBOOK_PATH.is_file()


def test_loads_expected_row_counts() -> None:
    repo = ParcelPilotRepository()
    assert len(repo.accounts) == 4
    assert len(repo.orders) == 6
    assert len(repo.tickets) == 7


def test_dataset_metadata() -> None:
    repo = ParcelPilotRepository()
    assert repo.metadata.snapshot == "2026-08-16 11:00 Asia/Kolkata"
    assert repo.metadata.currency == "INR"


def test_get_account_by_id() -> None:
    repo = ParcelPilotRepository()
    account = repo.get_account("ACCT-001")
    assert account is not None
    assert account.account_name == "Northstar Logistics"
    assert account.plan == AccountPlan.ENTERPRISE
    assert account.status == AccountStatus.ACTIVE
    assert account.premium_support is True
    assert account.contract_file == "05_Northstar_Logistics_Enterprise_Agreement.pdf"


def test_get_missing_account_returns_none() -> None:
    repo = ParcelPilotRepository()
    assert repo.get_account("ACCT-999") is None


def test_get_account_by_name() -> None:
    repo = ParcelPilotRepository()
    account = repo.get_account_by_name("lumenworks")
    assert account is not None
    assert account.account_id == "ACCT-002"


def test_get_order_and_account_orders() -> None:
    repo = ParcelPilotRepository()
    order = repo.get_order("ORD-1001")
    assert order is not None
    assert order.account_id == "ACCT-001"
    assert order.status == OrderStatus.BOOKED
    assert order.booked_at == datetime(2026, 8, 16, 9, 0)
    assert order.pickup_actual_at is None
    assert isinstance(order.shipment_fee_inr, int)

    account_orders = repo.list_orders(account_id="ACCT-001")
    assert {item.order_id for item in account_orders} == {"ORD-1001", "ORD-1002"}


def test_get_ticket_and_account_tickets() -> None:
    repo = ParcelPilotRepository()
    ticket = repo.get_ticket("TKT-501")
    assert ticket is not None
    assert ticket.account_id == "ACCT-001"
    assert ticket.status == TicketStatus.OPEN
    assert ticket.historical_resolution is None

    open_tickets = repo.list_tickets(status="open")
    assert open_tickets
    assert all(item.status == TicketStatus.OPEN for item in open_tickets)


def test_foreign_keys_resolve_to_accounts() -> None:
    repo = ParcelPilotRepository()
    account_ids = {account.account_id for account in repo.accounts}
    assert {order.account_id for order in repo.orders} <= account_ids
    assert {ticket.account_id for ticket in repo.tickets} <= account_ids
