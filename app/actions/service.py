"""ParcelPilot business-logic actions backed by lookup tools."""

from datetime import datetime

from app.actions.cancellation import evaluate_cancellation
from app.actions.models import (
    BulkUploadDecision,
    CancellationDecision,
    PickupStatusDecision,
    ServiceCreditDecision,
    SlaDecision,
)
from app.actions.product import evaluate_bulk_upload, interpret_pickup_status
from app.actions.service_credit import evaluate_service_credit
from app.actions.sla import get_first_response_target
from app.tools.tools import ParcelPilotTools


class ParcelPilotActions:
    """Focused support-operations actions for cancellation, credits, SLA, and product issues."""

    def __init__(self, tools: ParcelPilotTools | None = None) -> None:
        self.tools = tools or ParcelPilotTools()

    def evaluate_cancellation(
        self,
        order_id: str,
        requested_at: datetime | None = None,
    ) -> CancellationDecision:
        return evaluate_cancellation(order_id, self.tools, requested_at=requested_at)

    def evaluate_service_credit(
        self,
        order_id: str,
        as_of: datetime | None = None,
    ) -> ServiceCreditDecision:
        return evaluate_service_credit(order_id, self.tools, as_of=as_of)

    def get_first_response_target(self, account_id: str, severity: str) -> SlaDecision:
        return get_first_response_target(account_id, severity, self.tools)

    def evaluate_bulk_upload(
        self,
        account_id: str,
        csv_row_count: int | None = None,
    ) -> BulkUploadDecision:
        return evaluate_bulk_upload(account_id, self.tools, csv_row_count=csv_row_count)

    def interpret_pickup_status(
        self,
        order_id: str,
        as_of: datetime | None = None,
    ) -> PickupStatusDecision:
        return interpret_pickup_status(order_id, self.tools, as_of=as_of)
