"""Order cancellation decisions from the CURRENT SOP and customer agreements."""

from datetime import datetime

from app.actions.models import ActionStatus, CancellationDecision
from app.actions.policy import (
    CANCEL_GRACE_MINUTES,
    DEFAULT_CANCEL_FEE_INR,
    DRAFT_STATUS_GAP,
    NORTHSTAR_CONTRACT,
    SOP_FILENAME,
    has_northstar_agreement,
    minutes_between,
)
from app.data.models import OrderStatus
from app.tools.tools import ParcelPilotTools


def evaluate_cancellation(
    order_id: str,
    tools: ParcelPilotTools,
    requested_at: datetime | None = None,
) -> CancellationDecision:
    order = tools.get_order(order_id)
    if order is None:
        return CancellationDecision(
            status=ActionStatus.NOT_FOUND,
            order_id=order_id,
            reason=f"Order {order_id} was not found.",
        )

    account = tools.get_account(order.account_id)
    if account is None:
        return CancellationDecision(
            status=ActionStatus.NOT_FOUND,
            order_id=order_id,
            account_id=order.account_id,
            reason=f"Account {order.account_id} was not found for order {order_id}.",
        )

    sources = [SOP_FILENAME]
    waive_fee = has_northstar_agreement(account)
    if waive_fee:
        sources.append(NORTHSTAR_CONTRACT)

    if order.status == OrderStatus.DELIVERED:
        return CancellationDecision(
            status=ActionStatus.OK,
            order_id=order.order_id,
            account_id=account.account_id,
            can_cancel=False,
            use_return_to_origin=False,
            fee_waived_by_agreement=waive_fee,
            reason="DELIVERED shipments cannot be cancelled.",
            sources=sources,
            gaps=[DRAFT_STATUS_GAP],
        )

    if order.status == OrderStatus.PICKED_UP:
        return CancellationDecision(
            status=ActionStatus.OK,
            order_id=order.order_id,
            account_id=account.account_id,
            can_cancel=False,
            use_return_to_origin=True,
            fee_waived_by_agreement=waive_fee,
            reason=(
                "PICKED_UP shipments cannot be cancelled. "
                "Use the return-to-origin workflow if the customer wants the parcel returned."
            ),
            sources=sources,
            gaps=[DRAFT_STATUS_GAP],
        )

    effective_requested_at = requested_at or order.cancellation_requested_at
    if effective_requested_at is None:
        return CancellationDecision(
            status=ActionStatus.NEEDS_VERIFICATION,
            order_id=order.order_id,
            account_id=account.account_id,
            can_cancel=True,
            cancellation_fee_inr=None,
            fee_waived_by_agreement=waive_fee,
            reason=(
                "BOOKED shipments that are not yet PICKED_UP may be cancelled, "
                "but a cancellation request time is required to calculate any fee."
            ),
            sources=sources,
            gaps=[DRAFT_STATUS_GAP],
        )

    elapsed = minutes_between(order.booked_at, effective_requested_at)
    if waive_fee:
        fee = 0
        reason = (
            "Northstar may cancel any BOOKED shipment before pickup with no cancellation fee."
        )
    elif elapsed <= CANCEL_GRACE_MINUTES:
        fee = 0
        reason = (
            f"BOOKED shipment may be cancelled with no fee within {CANCEL_GRACE_MINUTES} "
            "minutes of booking."
        )
    else:
        fee = DEFAULT_CANCEL_FEE_INR
        reason = (
            f"BOOKED shipment may be cancelled. After {CANCEL_GRACE_MINUTES} minutes, "
            f"the cancellation fee is INR {DEFAULT_CANCEL_FEE_INR}."
        )

    return CancellationDecision(
        status=ActionStatus.OK,
        order_id=order.order_id,
        account_id=account.account_id,
        can_cancel=True,
        cancellation_fee_inr=fee,
        fee_waived_by_agreement=waive_fee,
        reason=reason,
        sources=sources,
        gaps=[DRAFT_STATUS_GAP],
    )
