"""Product capability and pickup-status decisions from the operations guide."""

from datetime import datetime

from app.actions.models import ActionStatus, BulkUploadDecision, PickupStatusDecision
from app.actions.policy import (
    BULK_UPLOAD_ROW_LIMIT,
    KI208_UNRELIABLE_ABOVE_ROWS,
    KI211_WEBHOOK_DELAY_MINUTES,
    OPS_GUIDE_FILENAME,
)
from app.data.models import AccountPlan, OrderStatus
from app.tools.tools import ParcelPilotTools


def evaluate_bulk_upload(
    account_id: str,
    tools: ParcelPilotTools,
    csv_row_count: int | None = None,
) -> BulkUploadDecision:
    account = tools.get_account(account_id)
    if account is None:
        return BulkUploadDecision(
            status=ActionStatus.NOT_FOUND,
            account_id=account_id,
            csv_row_count=csv_row_count,
            reason=f"Account {account_id} was not found.",
        )

    included = account.plan in {AccountPlan.GROWTH, AccountPlan.ENTERPRISE}
    if not included:
        return BulkUploadDecision(
            status=ActionStatus.OK,
            account_id=account.account_id,
            bulk_upload_included=False,
            supported_row_limit=None,
            csv_row_count=csv_row_count,
            within_supported_limit=False if csv_row_count is not None else None,
            reason="Bulk Upload is not included on the Standard plan.",
            sources=[OPS_GUIDE_FILENAME],
        )

    if csv_row_count is None:
        return BulkUploadDecision(
            status=ActionStatus.OK,
            account_id=account.account_id,
            bulk_upload_included=True,
            supported_row_limit=BULK_UPLOAD_ROW_LIMIT,
            reason=(
                f"Bulk Upload is available on {account.plan.value}. "
                f"Supported file size is up to {BULK_UPLOAD_ROW_LIMIT} rows per CSV."
            ),
            sources=[OPS_GUIDE_FILENAME],
        )

    if csv_row_count < 0:
        return BulkUploadDecision(
            status=ActionStatus.INVALID,
            account_id=account.account_id,
            bulk_upload_included=True,
            supported_row_limit=BULK_UPLOAD_ROW_LIMIT,
            csv_row_count=csv_row_count,
            reason="csv_row_count must be zero or greater.",
            sources=[OPS_GUIDE_FILENAME],
        )

    within_limit = csv_row_count <= BULK_UPLOAD_ROW_LIMIT
    if csv_row_count == KI208_UNRELIABLE_ABOVE_ROWS:
        return BulkUploadDecision(
            status=ActionStatus.NEEDS_VERIFICATION,
            account_id=account.account_id,
            bulk_upload_included=True,
            supported_row_limit=BULK_UPLOAD_ROW_LIMIT,
            csv_row_count=csv_row_count,
            within_supported_limit=within_limit,
            known_issue_ki208=False,
            reason=(
                "KI-208 describes intermittent failures above approximately 3,000 rows "
                "and recommends splitting files below 3,000 rows. At exactly 3,000 rows "
                "the guide is approximate; verify against the current known-issue notes "
                "before treating this as a confirmed KI-208 failure."
            ),
            sources=[OPS_GUIDE_FILENAME],
        )

    ki208 = csv_row_count > KI208_UNRELIABLE_ABOVE_ROWS
    workaround = (
        f"Split the upload into files below {KI208_UNRELIABLE_ABOVE_ROWS} rows. "
        "Individual shipment creation is unaffected."
        if ki208
        else None
    )
    if not within_limit:
        reason = (
            f"{csv_row_count} rows exceeds the supported product limit of "
            f"{BULK_UPLOAD_ROW_LIMIT} rows per CSV."
        )
    elif ki208:
        reason = (
            f"{csv_row_count} rows is within the supported {BULK_UPLOAD_ROW_LIMIT}-row limit, "
            f"but KI-208 causes intermittent failures above approximately "
            f"{KI208_UNRELIABLE_ABOVE_ROWS} rows."
        )
    else:
        reason = (
            f"{csv_row_count} rows is within the supported Bulk Upload limit "
            f"of {BULK_UPLOAD_ROW_LIMIT} rows."
        )

    return BulkUploadDecision(
        status=ActionStatus.OK,
        account_id=account.account_id,
        bulk_upload_included=True,
        supported_row_limit=BULK_UPLOAD_ROW_LIMIT,
        csv_row_count=csv_row_count,
        within_supported_limit=within_limit,
        known_issue_ki208=ki208,
        workaround=workaround,
        reason=reason,
        sources=[OPS_GUIDE_FILENAME],
    )


def interpret_pickup_status(
    order_id: str,
    tools: ParcelPilotTools,
    as_of: datetime | None = None,
) -> PickupStatusDecision:
    _ = as_of
    order = tools.get_order(order_id)
    if order is None:
        return PickupStatusDecision(
            status=ActionStatus.NOT_FOUND,
            order_id=order_id,
            reason=f"Order {order_id} was not found.",
        )

    confirmed = order.status == OrderStatus.PICKED_UP or order.pickup_actual_at is not None
    # KI-211 applies while SwiftShip is BOOKED with no pickup confirmation. The 20-minute
    # delay is from physical pickup, which is unknown, so do not clock it from the window end.
    delay_risk = (
        order.carrier == "SwiftShip"
        and order.status == OrderStatus.BOOKED
        and order.pickup_actual_at is None
    )
    if order.status == OrderStatus.BOOKED:
        meaning = (
            "BOOKED means the shipment is created but ParcelPilot has not yet received "
            "a pickup confirmation."
        )
    elif order.status == OrderStatus.PICKED_UP:
        meaning = "PICKED_UP means carrier pickup has been confirmed."
    else:
        meaning = f"Shipment status is {order.status.value}."

    if delay_risk:
        meaning += (
            f" KI-211: SwiftShip pickup webhooks can arrive up to {KI211_WEBHOOK_DELAY_MINUTES} "
            "minutes late. A parcel may already be collected while status remains BOOKED. "
            "Verify carrier status or wait through that delay window before telling the "
            "customer that pickup did not occur."
        )

    return PickupStatusDecision(
        status=ActionStatus.OK,
        order_id=order.order_id,
        account_id=order.account_id,
        shipment_status=order.status.value,
        carrier=order.carrier,
        pickup_confirmed=confirmed,
        swiftship_webhook_delay_risk=delay_risk,
        reason=meaning,
        sources=[OPS_GUIDE_FILENAME],
    )
