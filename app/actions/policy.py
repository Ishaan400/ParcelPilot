"""Policy constants taken from the supplied CURRENT documents.

Deprecated Support Policy v2 is never applied.
DRAFT order status appears in the SOP but is not present in the dataset or
OrderStatus enum; that case is therefore not implemented.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.data.models import Account, AccountPlan

SOP_FILENAME = "03_Cancellation_and_Service_Credit_SOP_v4.pdf"
SUPPORT_POLICY_V3_FILENAME = "01_Support_Policy_v3_CURRENT.pdf"
OPS_GUIDE_FILENAME = "04_Product_Operations_Guide_and_Known_Issues.pdf"
NORTHSTAR_CONTRACT = "05_Northstar_Logistics_Enterprise_Agreement.pdf"
LUMENWORKS_CONTRACT = "06_LumenWorks_Service_Agreement.pdf"
DEPRECATED_POLICY_FILENAME = "02_Support_Policy_v2_DEPRECATED.pdf"

# README sheet: Dataset snapshot = 2026-08-16 11:00 Asia/Kolkata
DATASET_TZ = ZoneInfo("Asia/Kolkata")
DATASET_SNAPSHOT = datetime(2026, 8, 16, 11, 0, tzinfo=DATASET_TZ)

CANCEL_GRACE_MINUTES = 30
DEFAULT_CANCEL_FEE_INR = 250

DEFAULT_CREDIT_DELAY_HOURS = 2.0
DEFAULT_CREDIT_CAP_INR = 500
DEFAULT_CREDIT_PERCENT = 10
MANAGER_APPROVAL_CREDIT_INR = 1000

LUMENWORKS_CREDIT_DELAY_HOURS = 4.0
LUMENWORKS_CREDIT_INR = 300
NORTHSTAR_MONTHLY_CREDIT_CAP_INR = 5000

BULK_UPLOAD_ROW_LIMIT = 5000
KI208_UNRELIABLE_ABOVE_ROWS = 3000
KI211_WEBHOOK_DELAY_MINUTES = 20


def parse_snapshot(snapshot: str) -> datetime:
    timestamp, timezone_name = snapshot.rsplit(" ", 1)
    naive = datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=ZoneInfo(timezone_name))


def localize_dataset_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=DATASET_TZ)
    return value.astimezone(DATASET_TZ)


def has_northstar_agreement(account: Account) -> bool:
    return account.contract_file == NORTHSTAR_CONTRACT


def has_lumenworks_agreement(account: Account) -> bool:
    return account.contract_file == LUMENWORKS_CONTRACT


def hours_between(start: datetime, end: datetime) -> float:
    return (
        localize_dataset_time(end) - localize_dataset_time(start)
    ).total_seconds() / 3600.0


def minutes_between(start: datetime, end: datetime) -> float:
    return (
        localize_dataset_time(end) - localize_dataset_time(start)
    ).total_seconds() / 60.0


DEFAULT_SLA: dict[AccountPlan, dict[str, dict[str, object]]] = {
    AccountPlan.ENTERPRISE: {
        "P1": {"target": "30 minutes, 24x7", "coverage_24x7": True, "weekend_coverage": None},
        "P2": {"target": "2 hours", "coverage_24x7": False, "weekend_coverage": None},
        "P3": {"target": "1 business day", "coverage_24x7": False, "weekend_coverage": None},
    },
    AccountPlan.GROWTH: {
        "P1": {"target": "2 business hours", "coverage_24x7": False, "weekend_coverage": None},
        "P2": {"target": "4 business hours", "coverage_24x7": False, "weekend_coverage": None},
        "P3": {"target": "2 business days", "coverage_24x7": False, "weekend_coverage": None},
    },
    AccountPlan.STANDARD: {
        "P1": {"target": "4 business hours", "coverage_24x7": False, "weekend_coverage": None},
        "P2": {"target": "1 business day", "coverage_24x7": False, "weekend_coverage": None},
        "P3": {"target": "2 business days", "coverage_24x7": False, "weekend_coverage": None},
    },
}

NORTHSTAR_SLA = {
    "P1": {"target": "15 minutes, 24x7", "coverage_24x7": True, "weekend_coverage": None},
    "P2": {"target": "1 hour", "coverage_24x7": False, "weekend_coverage": None},
    "P3": {"target": "8 business hours", "coverage_24x7": False, "weekend_coverage": None},
}

LUMENWORKS_SLA = {
    "P1": {"target": "2 business hours", "coverage_24x7": False, "weekend_coverage": False},
    "P2": {"target": "4 business hours", "coverage_24x7": False, "weekend_coverage": False},
    "P3": {"target": "2 business days", "coverage_24x7": False, "weekend_coverage": False},
}

BUSINESS_HOURS_GAP = (
    "Business-hour and business-day calendars are not defined in the supplied pack, "
    "so elapsed-time SLA breach cannot be computed for non-24x7 targets."
)

WEEKEND_COVERAGE_GAP = (
    "LumenWorks excludes weekend and after-hours coverage, but the pack does not "
    "define how that exclusion changes the SLA clock."
)

MONTHLY_CAP_GAP = (
    "Northstar monthly aggregate credits are capped at INR 5,000, but month-to-date "
    "credit totals are not in the dataset."
)

DRAFT_STATUS_GAP = (
    "The SOP allows DRAFT cancellations with no fee, but DRAFT is not present in the "
    "Excel order statuses."
)
