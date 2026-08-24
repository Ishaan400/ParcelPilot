"""Pydantic schemas for the ParcelPilot Excel dataset."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AccountPlan(str, Enum):
    ENTERPRISE = "Enterprise"
    GROWTH = "Growth"
    STANDARD = "Standard"


class AccountStatus(str, Enum):
    ACTIVE = "active"


class OrderStatus(str, Enum):
    BOOKED = "BOOKED"
    PICKED_UP = "PICKED_UP"
    DELIVERED = "DELIVERED"


class TicketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class TicketChannel(str, Enum):
    EMAIL = "email"
    CHAT = "chat"


class DatasetMetadata(BaseModel):
    title: str
    snapshot: str
    currency: str
    notes: str | None = None
    important: str | None = None


class Account(BaseModel):
    account_id: str
    account_name: str
    plan: AccountPlan
    status: AccountStatus
    csm: str
    contract_file: str | None = None
    premium_support: bool
    notes: str | None = None


class Order(BaseModel):
    order_id: str
    account_id: str
    carrier: str
    status: OrderStatus
    booked_at: datetime
    pickup_window_start: datetime
    pickup_window_end: datetime
    pickup_actual_at: datetime | None = None
    shipment_fee_inr: int
    carrier_fault: bool
    customer_fault: bool
    cancellation_requested_at: datetime | None = None
    notes: str | None = None


class Ticket(BaseModel):
    ticket_id: str
    account_id: str
    created_at: datetime
    status: TicketStatus
    subject: str
    description: str
    channel: TicketChannel
    assigned_to: str
    last_customer_message_at: datetime
    historical_resolution: str | None = Field(
        default=None,
        description="Historical context only; may be incorrect.",
    )
