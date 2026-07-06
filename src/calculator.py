def calculate_total(items: list[dict]) -> float:
    """Calculate the total price from a list of items.

    Args:
        items: List of dicts with "price" and "quantity" keys.

    Returns:
        The summed total of price * quantity for all items.

    Raises:
        TypeError: If items is not a list.
    """
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    return sum(item["price"] * item["quantity"] for item in items)


def apply_discount(total: float, discount_percent: float) -> float:
    """Apply a percentage discount to a total amount.

    Args:
        total: The original amount.
        discount_percent: Discount percentage (0-100).

    Returns:
        The discounted amount.

    Raises:
        ValueError: If discount_percent is not between 0 and 100.
    """
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("discount must be between 0 and 100")
    return total * (1 - discount_percent / 100)


def calculate_tax(amount: float, tax_rate: float) -> float:
    """Calculate tax amount from a base amount and tax rate.

    Args:
        amount: The base monetary amount.
        tax_rate: Tax rate as a percentage (0-100).

    Returns:
        The tax amount.

    Raises:
        TypeError: If amount or tax_rate is not a number.
        ValueError: If tax_rate is not between 0 and 100.
    """
    if not isinstance(amount, (int, float)):
        raise TypeError("amount must be a number")
    if not isinstance(tax_rate, (int, float)):
        raise TypeError("tax_rate must be a number")
    if tax_rate < 0 or tax_rate > 100:
        raise ValueError("tax_rate must be between 0 and 100")
    return amount * (tax_rate / 100)


def format_currency(amount: float) -> str:
    """Format a numeric amount as a US dollar currency string.

    Args:
        amount: The numeric amount to format.

    Returns:
        A dollar-formatted string (e.g., "$19.99").
    """
    return f"${amount:.2f}"
