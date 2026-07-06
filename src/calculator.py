def calculate_total(items: list[dict]) -> float:
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    return sum(item["price"] * item["quantity"] for item in items)


def apply_discount(total: float, discount_percent: float) -> float:
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("discount must be between 0 and 100")
    return total * (1 - discount_percent / 100)


def format_currency(amount: float) -> str:
    return f"${amount:.2f}"
