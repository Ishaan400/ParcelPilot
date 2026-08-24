"""Failed-pickup service credit decisions from the CURRENT SOP and agreements."""

from datetime import datetime

from app.actions.models import ActionStatus, ServiceCreditDecision
from app.actions.policy import (
    DEFAULT_CREDIT_CAP_INR,
    DEFAULT_CREDIT_DELAY_HOURS,
    DEFAULT_CREDIT_PERCENT,
    LUMENWORKS_CONTRACT,
    LUMENWORKS_CREDIT_DELAY_HOURS,
    LUMENWORKS_CREDIT_INR,
    MANAGER_APPROVAL_CREDIT_INR,
    MONTHLY_CAP_GAP,
    NORTHSTAR_CONTRACT,
    NORTHSTAR_MONTHLY_CREDIT_CAP_INR,
    OPS_GUIDE_FILENAME,
    SOP_FILENAME,
    has_lumenworks_agreement,
    has_northstar_agreement,
    hours_between,
    DATASET_SNAPSHOT,
)
from app.data.models import OrderStatus
from app.tools.tools import ParcelPilotTools


def evaluate_service_credit(
    order_id: str,
    tools: ParcelPilotTools,
    as_of: datetime | None = None,
) -> ServiceCreditDecision:
    order = tools.get_order(order_id)
    if order is None:
        return ServiceCreditDecision(
            status=ActionStatus.NOT_FOUND,
            order_id=order_id,
            reason=f"Order {order_id} was not found.",
        )

    account = tools.get_account(order.account_id)
    if account is None:
        return ServiceCreditDecision(
            status=ActionStatus.NOT_FOUND,
            order_id=order_id,
            account_id=order.account_id,
            reason=f"Account {order.account_id} was not found for order {order_id}.",
        )

    sources = [SOP_FILENAME]
    gaps: list[str] = []
    monthly_cap: int | None = None
    if has_lumenworks_agreement(account):
        sources.append(LUMENWORKS_CONTRACT)
        delay_hours = LUMENWORKS_CREDIT_DELAY_HOURS
    else:
        delay_hours = DEFAULT_CREDIT_DELAY_HOURS
    if has_northstar_agreement(account):
        sources.append(NORTHSTAR_CONTRACT)
        monthly_cap = NORTHSTAR_MONTHLY_CREDIT_CAP_INR
        gaps.append(MONTHLY_CAP_GAP)

    effective_as_of = as_of or DATASET_SNAPSHOT
    pickup_time = order.pickup_actual_at
    swiftship_unconfirmed = (
        order.carrier == "SwiftShip"
        and order.status == OrderStatus.BOOKED
        and pickup_time is None
    )
    if swiftship_unconfirmed:
        sources.append(OPS_GUIDE_FILENAME)

    if pickup_time is None:
        reference_time = effective_as_of
        timing_label = "dataset snapshot"
    else:
        reference_time = pickup_time
        timing_label = "recorded pickup time"

    hours_late = hours_between(order.pickup_window_end, reference_time)

    if swiftship_unconfirmed:
        return ServiceCreditDecision(
            status=ActionStatus.NEEDS_VERIFICATION,
            order_id=order.order_id,
            account_id=account.account_id,
            eligible=False,
            delay_threshold_hours=delay_hours,
            hours_past_window_end=hours_late,
            monthly_aggregate_cap_inr=monthly_cap,
            reason=(
                "SwiftShip pickup webhooks can arrive up to 20 minutes late while status "
                "remains BOOKED (KI-211). Pickup timing is not confirmed. The SOP does not "
                "allow promising a credit until pickup timing is verified."
            ),
            sources=sources,
            gaps=gaps,
        )

    if hours_late <= delay_hours:
        return ServiceCreditDecision(
            status=ActionStatus.OK,
            order_id=order.order_id,
            account_id=account.account_id,
            eligible=False,
            delay_threshold_hours=delay_hours,
            hours_past_window_end=hours_late,
            monthly_aggregate_cap_inr=monthly_cap,
            reason=(
                f"Pickup timing from {timing_label} is not more than {delay_hours:g} hours "
                "past the scheduled pickup window end."
            ),
            sources=sources,
            gaps=gaps,
        )

    if not order.carrier_fault or order.customer_fault:
        return ServiceCreditDecision(
            status=ActionStatus.OK,
            order_id=order.order_id,
            account_id=account.account_id,
            eligible=False,
            delay_threshold_hours=delay_hours,
            hours_past_window_end=hours_late,
            monthly_aggregate_cap_inr=monthly_cap,
            reason=(
                "Service credit requires carrier fault and no customer-caused issue. "
                f"carrier_fault={order.carrier_fault}, customer_fault={order.customer_fault}."
            ),
            sources=sources,
            gaps=gaps,
        )

    if has_lumenworks_agreement(account):
        credit = LUMENWORKS_CREDIT_INR
        reason = (
            "LumenWorks failed-pickup credit is a fixed INR 300 when pickup is more than "
            "4 hours past the window end, the carrier is at fault, and the customer is not at fault."
        )
    else:
        percent_amount = order.shipment_fee_inr * DEFAULT_CREDIT_PERCENT // 100
        credit = min(DEFAULT_CREDIT_CAP_INR, percent_amount)
        reason = (
            "Default failed-pickup credit is the lower of INR 500 or 10% of the shipment fee."
        )

    return ServiceCreditDecision(
        status=ActionStatus.OK,
        order_id=order.order_id,
        account_id=account.account_id,
        eligible=True,
        credit_inr=credit,
        requires_manager_approval=credit > MANAGER_APPROVAL_CREDIT_INR,
        delay_threshold_hours=delay_hours,
        hours_past_window_end=hours_late,
        monthly_aggregate_cap_inr=monthly_cap,
        reason=reason,
        sources=sources,
        gaps=gaps,
    )
