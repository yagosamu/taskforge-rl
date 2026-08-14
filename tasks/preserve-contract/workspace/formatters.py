"""Public display formatters."""


def format_user(record: dict[str, object]) -> str:
    """Format a user record."""
    return f"User:{record['id']}:{str(record['name']).strip()}"


def format_order(record: dict[str, object]) -> str:
    """Format an order record."""
    return f"Order:{record['id']}:{record['name']}"


def format_invoice(record: dict[str, object]) -> str:
    """Format an invoice record."""
    return f"Invoice:{record['id']}:{record['name']}"


def format_ticket(record: dict[str, object]) -> str:
    """Format a ticket record."""
    return f"Ticket:{record['id']}:{record['name']}"
