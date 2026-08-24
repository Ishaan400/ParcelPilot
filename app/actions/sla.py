"""First-response SLA from Support Policy v3 and customer agreements."""

from app.actions.models import ActionStatus, SlaDecision
from app.actions.policy import (
    BUSINESS_HOURS_GAP,
    DEFAULT_SLA,
    LUMENWORKS_CONTRACT,
    LUMENWORKS_SLA,
    NORTHSTAR_CONTRACT,
    NORTHSTAR_SLA,
    SUPPORT_POLICY_V3_FILENAME,
    WEEKEND_COVERAGE_GAP,
    has_lumenworks_agreement,
    has_northstar_agreement,
)
from app.tools.tools import ParcelPilotTools

VALID_SEVERITIES = {"P1", "P2", "P3"}


def get_first_response_target(
    account_id: str,
    severity: str,
    tools: ParcelPilotTools,
) -> SlaDecision:
    normalized = severity.strip().upper()
    if normalized not in VALID_SEVERITIES:
        return SlaDecision(
            status=ActionStatus.INVALID,
            account_id=account_id,
            severity=severity,
            reason="Severity must be P1, P2, or P3.",
        )

    account = tools.get_account(account_id)
    if account is None:
        return SlaDecision(
            status=ActionStatus.NOT_FOUND,
            account_id=account_id,
            severity=normalized,
            reason=f"Account {account_id} was not found.",
        )

    sources = [SUPPORT_POLICY_V3_FILENAME]
    gaps = [BUSINESS_HOURS_GAP]
    uses_agreement = False

    if has_northstar_agreement(account):
        spec = NORTHSTAR_SLA[normalized]
        sources.append(NORTHSTAR_CONTRACT)
        uses_agreement = True
        reason = (
            "Northstar first-response targets replace ParcelPilot standard support-policy targets."
        )
    elif has_lumenworks_agreement(account):
        spec = LUMENWORKS_SLA[normalized]
        sources.append(LUMENWORKS_CONTRACT)
        uses_agreement = True
        gaps.append(WEEKEND_COVERAGE_GAP)
        reason = (
            "LumenWorks agreement support terms apply, including no weekend or after-hours coverage."
        )
    else:
        spec = DEFAULT_SLA[account.plan][normalized]
        reason = (
            f"Default Support Policy v3 first-response target for plan {account.plan.value}."
        )

    return SlaDecision(
        status=ActionStatus.OK,
        account_id=account.account_id,
        severity=normalized,
        target=str(spec["target"]),
        coverage_24x7=bool(spec["coverage_24x7"]),
        weekend_coverage=(
            None if spec["weekend_coverage"] is None else bool(spec["weekend_coverage"])
        ),
        escalate_immediately=normalized == "P1",
        uses_customer_agreement=uses_agreement,
        reason=reason,
        sources=sources,
        gaps=gaps,
    )
