from datetime import datetime

from app.actions.models import ActionStatus
from app.actions.policy import (
    DATASET_SNAPSHOT,
    DATASET_TZ,
    LUMENWORKS_CREDIT_INR,
    NORTHSTAR_CONTRACT,
    SOP_FILENAME,
    SUPPORT_POLICY_V3_FILENAME,
)
from app.actions.service import ParcelPilotActions


def test_northstar_booked_cancellation_waives_fee() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_cancellation("ORD-1001")
    assert result.status == ActionStatus.OK
    assert result.can_cancel is True
    assert result.cancellation_fee_inr == 0
    assert result.fee_waived_by_agreement is True
    assert NORTHSTAR_CONTRACT in result.sources


def test_lumenworks_booked_cancellation_after_grace_charges_fee() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_cancellation("ORD-2001")
    assert result.status == ActionStatus.OK
    assert result.can_cancel is True
    assert result.cancellation_fee_inr == 250
    assert result.fee_waived_by_agreement is False
    assert SOP_FILENAME in result.sources


def test_standard_booked_cancellation_within_grace_is_free() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_cancellation("ORD-3001")
    assert result.status == ActionStatus.OK
    assert result.can_cancel is True
    assert result.cancellation_fee_inr == 0


def test_picked_up_order_uses_return_to_origin() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_cancellation("ORD-1002")
    assert result.status == ActionStatus.OK
    assert result.can_cancel is False
    assert result.use_return_to_origin is True
    assert result.cancellation_fee_inr is None


def test_delivered_order_cannot_be_cancelled() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_cancellation("ORD-4001")
    assert result.status == ActionStatus.OK
    assert result.can_cancel is False
    assert result.use_return_to_origin is False


def test_cancellation_without_request_time_needs_verification() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_cancellation("ORD-2002")
    assert result.status == ActionStatus.NEEDS_VERIFICATION
    assert result.can_cancel is True
    assert result.cancellation_fee_inr is None


def test_cancellation_requested_at_override() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_cancellation(
        "ORD-2002",
        requested_at=datetime(2026, 8, 16, 4, 50),
    )
    assert result.status == ActionStatus.OK
    assert result.can_cancel is True
    assert result.cancellation_fee_inr == 0


def test_cancellation_order_not_found() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_cancellation("ORD-9999")
    assert result.status == ActionStatus.NOT_FOUND
    assert result.can_cancel is False


def test_lumenworks_failed_pickup_credit() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_service_credit("ORD-2002")
    assert result.status == ActionStatus.OK
    assert result.eligible is True
    assert result.credit_inr == LUMENWORKS_CREDIT_INR
    assert result.delay_threshold_hours == 4.0
    assert result.requires_manager_approval is False


def test_default_credit_not_eligible_inside_window() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_service_credit("ORD-3001")
    assert result.status == ActionStatus.OK
    assert result.eligible is False
    assert result.credit_inr is None
    assert result.delay_threshold_hours == 2.0


def test_credit_requires_carrier_fault() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_service_credit(
        "ORD-4001",
        as_of=datetime(2026, 8, 16, 11, 0),
    )
    assert result.status == ActionStatus.OK
    assert result.eligible is False


def test_swiftship_booked_credit_needs_verification() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_service_credit("ORD-1001")
    assert result.status == ActionStatus.NEEDS_VERIFICATION
    assert result.eligible is False


def test_service_credit_order_not_found() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_service_credit("ORD-9999")
    assert result.status == ActionStatus.NOT_FOUND


def test_northstar_sla_overrides_policy() -> None:
    actions = ParcelPilotActions()
    result = actions.get_first_response_target("ACCT-001", "p1")
    assert result.status == ActionStatus.OK
    assert result.target == "15 minutes, 24x7"
    assert result.coverage_24x7 is True
    assert result.escalate_immediately is True
    assert result.uses_customer_agreement is True
    assert SUPPORT_POLICY_V3_FILENAME in result.sources
    assert NORTHSTAR_CONTRACT in result.sources


def test_default_enterprise_sla() -> None:
    actions = ParcelPilotActions()
    result = actions.get_first_response_target("ACCT-004", "P2")
    assert result.status == ActionStatus.OK
    assert result.target == "2 hours"
    assert result.uses_customer_agreement is False
    assert result.escalate_immediately is False


def test_standard_plan_p3_sla() -> None:
    actions = ParcelPilotActions()
    result = actions.get_first_response_target("ACCT-003", "P3")
    assert result.status == ActionStatus.OK
    assert result.target == "2 business days"


def test_lumenworks_sla_notes_no_weekend_coverage() -> None:
    actions = ParcelPilotActions()
    result = actions.get_first_response_target("ACCT-002", "P1")
    assert result.status == ActionStatus.OK
    assert result.target == "2 business hours"
    assert result.weekend_coverage is False
    assert result.escalate_immediately is True


def test_sla_invalid_severity() -> None:
    actions = ParcelPilotActions()
    result = actions.get_first_response_target("ACCT-001", "P4")
    assert result.status == ActionStatus.INVALID


def test_sla_account_not_found() -> None:
    actions = ParcelPilotActions()
    result = actions.get_first_response_target("ACCT-999", "P1")
    assert result.status == ActionStatus.NOT_FOUND


def test_bulk_upload_not_on_standard() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_bulk_upload("ACCT-003", csv_row_count=100)
    assert result.status == ActionStatus.OK
    assert result.bulk_upload_included is False
    assert result.within_supported_limit is False


def test_bulk_upload_growth_ki208() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_bulk_upload("ACCT-002", csv_row_count=4200)
    assert result.status == ActionStatus.OK
    assert result.bulk_upload_included is True
    assert result.within_supported_limit is True
    assert result.known_issue_ki208 is True
    assert result.workaround is not None


def test_bulk_upload_exceeds_product_limit() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_bulk_upload("ACCT-001", csv_row_count=6000)
    assert result.status == ActionStatus.OK
    assert result.within_supported_limit is False
    assert result.known_issue_ki208 is True


def test_bulk_upload_capability_without_row_count() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_bulk_upload("ACCT-004")
    assert result.status == ActionStatus.OK
    assert result.bulk_upload_included is True
    assert result.supported_row_limit == 5000
    assert result.csv_row_count is None


def test_bulk_upload_invalid_row_count() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_bulk_upload("ACCT-001", csv_row_count=-1)
    assert result.status == ActionStatus.INVALID


def test_bulk_upload_account_not_found() -> None:
    actions = ParcelPilotActions()
    result = actions.evaluate_bulk_upload("ACCT-999")
    assert result.status == ActionStatus.NOT_FOUND


def test_pickup_status_swiftship_booked_warns_ki211() -> None:
    actions = ParcelPilotActions()
    result = actions.interpret_pickup_status("ORD-1001")
    assert result.status == ActionStatus.OK
    assert result.shipment_status == "BOOKED"
    assert result.pickup_confirmed is False
    assert result.swiftship_webhook_delay_risk is True


def test_pickup_status_picked_up_is_confirmed() -> None:
    actions = ParcelPilotActions()
    result = actions.interpret_pickup_status("ORD-1002")
    assert result.status == ActionStatus.OK
    assert result.pickup_confirmed is True
    assert result.swiftship_webhook_delay_risk is False


def test_pickup_status_not_found() -> None:
    actions = ParcelPilotActions()
    result = actions.interpret_pickup_status("ORD-9999")
    assert result.status == ActionStatus.NOT_FOUND


def test_deprecated_support_policy_v2_is_never_used() -> None:
    actions = ParcelPilotActions()
    results = [
        actions.evaluate_cancellation("ORD-1001"),
        actions.evaluate_cancellation("ORD-2001"),
        actions.evaluate_service_credit("ORD-2002"),
        actions.get_first_response_target("ACCT-001", "P1"),
        actions.get_first_response_target("ACCT-003", "P3"),
        actions.evaluate_bulk_upload("ACCT-002", csv_row_count=4200),
        actions.interpret_pickup_status("ORD-1001"),
    ]
    for result in results:
        assert all("v2" not in source.casefold() for source in result.sources)
        assert all("DEPRECATED" not in source for source in result.sources)


def test_dataset_snapshot_uses_asia_kolkata() -> None:
    assert DATASET_SNAPSHOT.tzinfo is not None
    assert str(DATASET_SNAPSHOT.tzinfo) == "Asia/Kolkata"
    assert DATASET_SNAPSHOT == datetime(2026, 8, 16, 11, 0, tzinfo=DATASET_TZ)


def test_ki211_unconfirmed_swiftship_stays_unverified() -> None:
    """KI-211 delay is from physical pickup, which is unknown while status is BOOKED."""
    actions = ParcelPilotActions()
    later = datetime(2026, 8, 16, 11, 51, tzinfo=DATASET_TZ)
    pickup = actions.interpret_pickup_status("ORD-1001", as_of=later)
    assert pickup.pickup_confirmed is False
    assert pickup.swiftship_webhook_delay_risk is True
    credit = actions.evaluate_service_credit("ORD-1001", as_of=later)
    assert credit.status == ActionStatus.NEEDS_VERIFICATION
    assert credit.eligible is False
    assert "KI-211" in credit.reason


def test_bulk_upload_ki208_approximate_3000_needs_verification() -> None:
    actions = ParcelPilotActions()
    at_threshold = actions.evaluate_bulk_upload("ACCT-002", csv_row_count=3000)
    assert at_threshold.status == ActionStatus.NEEDS_VERIFICATION
    below = actions.evaluate_bulk_upload("ACCT-002", csv_row_count=2999)
    assert below.status == ActionStatus.OK
    assert below.known_issue_ki208 is False


def test_24x7_target_does_not_invent_weekend_flag() -> None:
    actions = ParcelPilotActions()
    northstar = actions.get_first_response_target("ACCT-001", "P1")
    assert northstar.coverage_24x7 is True
    assert northstar.weekend_coverage is None
    enterprise = actions.get_first_response_target("ACCT-004", "P1")
    assert enterprise.coverage_24x7 is True
    assert enterprise.weekend_coverage is None
