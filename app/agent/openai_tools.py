"""OpenAI function-calling tool schemas."""

LOOKUP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_account",
            "description": "Get one account by account_id (for example ACCT-001).",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_by_name",
            "description": "Get one account by customer/account name.",
            "parameters": {
                "type": "object",
                "properties": {"account_name": {"type": "string"}},
                "required": ["account_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_accounts",
            "description": "List all accounts in the dataset.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Get one order/shipment by order_id (for example ORD-1001).",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders",
            "description": "List orders, optionally filtered by account_id.",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket",
            "description": "Get one support ticket by ticket_id (for example TKT-501).",
            "parameters": {
                "type": "object",
                "properties": {"ticket_id": {"type": "string"}},
                "required": ["ticket_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tickets",
            "description": "List tickets, optionally filtered by account_id and status (open or closed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search CURRENT policy, SOP, product, and agreement PDFs. "
                "Returns matching text with source_filename."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
]

ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "evaluate_cancellation",
            "description": (
                "Evaluate whether an order may be cancelled and any fee, using the "
                "action layer. Does not cancel the shipment."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "requested_at": {
                        "type": ["string", "null"],
                        "description": "Optional cancellation request time (YYYY-MM-DD HH:MM). Omit or pass null to use the order record.",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_service_credit",
            "description": (
                "Evaluate failed-pickup service credit eligibility and amount. "
                "Does not apply the credit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "as_of": {
                        "type": "string",
                        "description": "Optional evaluation time (YYYY-MM-DD HH:MM).",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_first_response_target",
            "description": "Get the first-response SLA target for an account and severity P1, P2, or P3.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "severity": {"type": "string"},
                },
                "required": ["account_id", "severity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_bulk_upload",
            "description": "Evaluate Bulk Upload plan capability, row limits, and KI-208.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "csv_row_count": {
                        "type": ["integer", "null"],
                        "description": "Optional CSV row count. Omit or pass null when not provided.",
                    },
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "interpret_pickup_status",
            "description": "Interpret BOOKED vs PICKED_UP and SwiftShip KI-211 delay risk.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
]

CONFIRMATION_TOOL = {
    "type": "function",
    "function": {
        "name": "request_action_confirmation",
        "description": (
            "Prepare a structured confirmation request for a recommended "
            "state-changing action. Does not execute the action."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "description": "For example cancel_shipment, apply_service_credit, escalate.",
                },
                "summary": {"type": "string"},
                "order_id": {"type": "string"},
                "account_id": {"type": "string"},
                "payload": {"type": "object"},
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["action_type", "summary"],
        },
    },
}

OPENAI_TOOLS = LOOKUP_TOOLS + ACTION_TOOLS + [CONFIRMATION_TOOL]
