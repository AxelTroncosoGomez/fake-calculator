import pytest

from src.calculator import apply_discount, calculate_total, format_currency


class TestCalculateTotal:
    def test_sums_item_prices_multiplied_by_quantities(self):
        items = [
            {"price": 10, "quantity": 2},
            {"price": 5, "quantity": 3},
        ]
        assert calculate_total(items) == 35

    def test_returns_zero_for_empty_list(self):
        assert calculate_total([]) == 0

    def test_raises_for_non_list_input(self):
        with pytest.raises(TypeError, match="items must be a list"):
            calculate_total("not-a-list")


class TestApplyDiscount:
    def test_applies_percentage_discount_correctly(self):
        assert apply_discount(100, 20) == 80

    def test_raises_for_negative_discount(self):
        with pytest.raises(ValueError, match="discount must be between 0 and 100"):
            apply_discount(100, -5)

    def test_raises_for_discount_over_100(self):
        with pytest.raises(ValueError, match="discount must be between 0 and 100"):
            apply_discount(100, 150)


class TestFormatCurrency:
    def test_formats_numbers_as_currency(self):
        assert format_currency(19.99) == "$19.99"

    def test_formats_zero_correctly(self):
        assert format_currency(0) == "$0.00"
