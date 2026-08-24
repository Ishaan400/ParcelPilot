"""Structured action results."""

from enum import Enum

from pydantic import BaseModel, Field


class ActionStatus(str, Enum):
    OK = "ok"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    NEEDS_VERIFICATION = "needs_verification"


class CancellationDecision(BaseModel):
    status: ActionStatus
    order_id: str
    account_id: str | None = None
    can_cancel: bool = False
    cancellation_fee_inr: int | None = None
    use_return_to_origin: bool = False
    fee_waived_by_agreement: bool = False
    reason: str
    sources: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ServiceCreditDecision(BaseModel):
    status: ActionStatus
    order_id: str
    account_id: str | None = None
    eligible: bool = False
    credit_inr: int | None = None
    requires_manager_approval: bool = False
    delay_threshold_hours: float | None = None
    hours_past_window_end: float | None = None
    monthly_aggregate_cap_inr: int | None = None
    reason: str
    sources: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class SlaDecision(BaseModel):
    status: ActionStatus
    account_id: str | None = None
    severity: str | None = None
    target: str | None = None
    coverage_24x7: bool | None = None
    weekend_coverage: bool | None = None
    escalate_immediately: bool = False
    uses_customer_agreement: bool = False
    reason: str
    sources: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class BulkUploadDecision(BaseModel):
    status: ActionStatus
    account_id: str | None = None
    bulk_upload_included: bool = False
    supported_row_limit: int | None = None
    csv_row_count: int | None = None
    within_supported_limit: bool | None = None
    known_issue_ki208: bool = False
    workaround: str | None = None
    reason: str
    sources: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class PickupStatusDecision(BaseModel):
    status: ActionStatus
    order_id: str
    account_id: str | None = None
    shipment_status: str | None = None
    carrier: str | None = None
    pickup_confirmed: bool | None = None
    swiftship_webhook_delay_risk: bool = False
    reason: str
    sources: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
