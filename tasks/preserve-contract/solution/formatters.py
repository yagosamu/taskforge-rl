"""Public display formatters."""


def _format(kind: str, record: dict[str, object]) -> str:
    return f"{kind}:{record['id']}:{str(record['name']).strip()}"


def format_user(record: dict[str, object]) -> str:
    """Format a user record."""
    return _format("User", record)


def format_order(record: dict[str, object]) -> str:
    """Format an order record."""
    return _format("Order", record)


def format_invoice(record: dict[str, object]) -> str:
    """Format an invoice record."""
    return _format("Invoice", record)


def format_ticket(record: dict[str, object]) -> str:
    """Format a ticket record."""
    return _format("Ticket", record)
