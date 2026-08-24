"""Thin tool wrappers over ParcelPilot data and document retrieval."""

from app.data.models import Account, Order, Ticket
from app.data.repository import ParcelPilotRepository
from app.retrieval.models import RetrievalResult
from app.retrieval.retriever import DocumentRetriever

DEPRECATED_POLICY_FILENAME = "02_Support_Policy_v2_DEPRECATED.pdf"


def _is_deprecated_policy(filename: str) -> bool:
    name = filename.casefold()
    return "deprecated" in name or "support_policy_v2" in name


class ParcelPilotTools:
    """Structured lookup and search tools for the future support agent."""

    def __init__(
        self,
        repository: ParcelPilotRepository | None = None,
        retriever: DocumentRetriever | None = None,
    ) -> None:
        self.repository = repository or ParcelPilotRepository()
        self.retriever = retriever or DocumentRetriever()

    def get_account(self, account_id: str) -> Account | None:
        return self.repository.get_account(account_id)

    def get_account_by_name(self, account_name: str) -> Account | None:
        return self.repository.get_account_by_name(account_name)

    def list_accounts(self) -> list[Account]:
        return self.repository.list_accounts()

    def get_order(self, order_id: str) -> Order | None:
        return self.repository.get_order(order_id)

    def list_orders(self, account_id: str | None = None) -> list[Order]:
        return self.repository.list_orders(account_id=account_id)

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        return self.repository.get_ticket(ticket_id)

    def list_tickets(
        self,
        account_id: str | None = None,
        status: str | None = None,
    ) -> list[Ticket]:
        return self.repository.list_tickets(account_id=account_id, status=status)

    def search_documents(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        # Over-fetch so excluding deprecated v2 still fills top_k current chunks.
        raw = self.retriever.search(query, top_k=max(top_k * 3, top_k + 5))
        current = [
            hit
            for hit in raw
            if not _is_deprecated_policy(hit.source_filename)
        ]
        return current[:top_k]
