"""Pricing rules."""

TAX_RATES = {"CA": 0.075, "NY": 0.08}


def tax_rate(state: str) -> float:
    """Return the sales tax rate for a state code."""
    return TAX_RATES.get(state, 0.0)
