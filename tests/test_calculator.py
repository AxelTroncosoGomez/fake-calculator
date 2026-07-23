import pytest

from src.calculator import (
    apply_discount,
    calculate_tax,
    calculate_total,
    format_currency,
)


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

    def test_raises_for_bool_total(self):
        with pytest.raises(TypeError, match="total must be a number"):
            apply_discount(True, 20)

    def test_raises_for_bool_discount(self):
        with pytest.raises(TypeError, match="discount_percent must be a number"):
            apply_discount(100, False)


class TestCalculateTax:
    def test_calculates_tax_for_positive_amount(self):
        assert calculate_tax(100, 8) == 8.0

    def test_returns_zero_for_zero_tax_rate(self):
        assert calculate_tax(100, 0) == 0.0

    def test_handles_negative_amount(self):
        assert calculate_tax(-50, 8) == -4.0

    def test_raises_for_non_numeric_amount(self):
        with pytest.raises(TypeError, match="amount must be a number"):
            calculate_tax("100", 8)

    def test_raises_for_bool_amount(self):
        with pytest.raises(TypeError, match="amount must be a number"):
            calculate_tax(True, 8)

    def test_raises_for_non_numeric_tax_rate(self):
        with pytest.raises(TypeError, match="tax_rate must be a number"):
            calculate_tax(100, "8%")

    def test_raises_for_bool_tax_rate(self):
        with pytest.raises(TypeError, match="tax_rate must be a number"):
            calculate_tax(100, False)

    def test_raises_for_negative_tax_rate(self):
        with pytest.raises(ValueError, match="tax_rate must be between 0 and 100"):
            calculate_tax(100, -5)

    def test_raises_for_tax_rate_over_100(self):
        with pytest.raises(ValueError, match="tax_rate must be between 0 and 100"):
            calculate_tax(100, 150)


class TestFormatCurrency:
    def test_formats_numbers_as_currency(self):
        assert format_currency(19.99) == "$19.99"

    def test_formats_zero_correctly(self):
        assert format_currency(0) == "$0.00"
