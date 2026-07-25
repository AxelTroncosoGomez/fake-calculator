"""Unit tests for FakeCalculatorWindow (PySide6 UI layer)."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from src.calculator import apply_discount, calculate_tax, calculate_total
from src.fake_calculator_ui import FakeCalculatorWindow
from src.utils import validate_email


@pytest.fixture
def window(qapp):
    """Create a fresh FakeCalculatorWindow for each test."""
    return FakeCalculatorWindow()


# ---------------------------------------------------------------------------
# Item management
# ---------------------------------------------------------------------------


class TestItemManagement:
    def test_add_item_appends_row(self, window):
        window._on_add_item()
        assert window._table.rowCount() == 1

    def test_add_multiple_items(self, window):
        for _ in range(3):
            window._on_add_item()
        assert window._table.rowCount() == 3

    def test_add_item_default_values(self, window):
        window._on_add_item()
        assert window._table.item(0, 0).text() == ""
        assert window._table.item(0, 1).text() == "0"
        assert window._table.item(0, 2).text() == "1"
        assert window._table.item(0, 3).text() == "$0.00"

    def test_add_item_line_total_is_not_editable(self, window):
        window._on_add_item()
        flags = window._table.item(0, 3).flags()
        assert not (flags & Qt.ItemFlag.ItemIsEditable)  # type: ignore[union-attr]

    def test_remove_item_reduces_row_count(self, window):
        window._on_add_item()
        window._on_add_item()
        window._table.selectRow(0)
        window._on_remove_item()
        assert window._table.rowCount() == 1

    def test_remove_item_with_no_selection_does_nothing(self, window):
        window._on_add_item()
        window._table.setCurrentCell(-1, -1)
        window._on_remove_item()
        assert window._table.rowCount() == 1


# ---------------------------------------------------------------------------
# Item collection / parsing
# ---------------------------------------------------------------------------


class TestCollectItems:
    def test_collect_empty_table(self, window):
        assert window._collect_items() == []

    def test_collect_parses_price_and_quantity(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("10.50")
        window._table.item(0, 2).setText("3")
        items = window._collect_items()
        assert items[0]["price"] == 10.50
        assert items[0]["quantity"] == 3

    def test_collect_truncates_long_name(self, window):
        window._on_add_item()
        window._table.item(0, 0).setText("A" * 50)
        items = window._collect_items()
        assert len(items[0]["name"]) == FakeCalculatorWindow.MAX_ITEM_NAME_LENGTH + 3

    def test_collect_treats_invalid_price_as_zero(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("not-a-number")
        items = window._collect_items()
        assert items[0]["price"] == 0.0

    def test_collect_treats_invalid_quantity_as_zero(self, window):
        window._on_add_item()
        window._table.item(0, 2).setText("xyz")
        items = window._collect_items()
        assert items[0]["quantity"] == 0

    def test_collect_handles_missing_cells(self, window):
        window._on_add_item()
        window._table.takeItem(0, 1)
        items = window._collect_items()
        assert items[0]["price"] == 0.0


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------


class TestSubtotal:
    def test_subtotal_sums_items(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("10")
        window._table.item(0, 2).setText("2")
        window._on_add_item()
        window._table.item(1, 1).setText("5")
        window._table.item(1, 2).setText("3")
        assert window.subtotal() == 35.0

    def test_subtotal_zero_for_empty_table(self, window):
        assert window.subtotal() == 0.0


class TestDiscount:
    def test_discounted_amount_applies_percentage(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._discount_input.setText("20")
        assert window.discounted_amount() == 80.0

    def test_discounted_amount_zero_percent(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("50")
        window._table.item(0, 2).setText("2")
        window._discount_input.setText("0")
        assert window.discounted_amount() == 100.0

    def test_discount_over_100_falls_back_to_subtotal(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._discount_input.setText("150")
        assert window.discounted_amount() == 100.0

    def test_negative_discount_falls_back_to_subtotal(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._discount_input.setText("-10")
        assert window.discounted_amount() == 100.0

    def test_non_numeric_discount_treated_as_zero(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._discount_input.setText("abc")
        assert window.discount_percent() == 0.0


class TestTax:
    def test_tax_amount_positive_rate(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._tax_input.setText("8")
        assert window.tax_amount() == 8.0

    def test_tax_amount_zero_rate(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._tax_input.setText("0")
        assert window.tax_amount() == 0.0

    def test_tax_over_100_falls_back_to_zero(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._tax_input.setText("150")
        assert window.tax_amount() == 0.0

    def test_non_numeric_tax_treated_as_zero(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._tax_input.setText("xyz")
        assert window.tax_rate() == 0.0


class TestFinalTotal:
    def test_total_sums_discounted_and_tax(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._discount_input.setText("10")
        window._tax_input.setText("5")
        assert window.final_total() == 94.5

    def test_total_zero_for_empty(self, window):
        assert window.final_total() == 0.0

    def test_total_incorporates_discount_and_tax(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("200")
        window._table.item(0, 2).setText("2")
        window._discount_input.setText("25")
        window._tax_input.setText("10")
        assert window.final_total() == 330.0


# ---------------------------------------------------------------------------
# Refresh line total
# ---------------------------------------------------------------------------


class TestRefreshLineTotal:
    def test_updates_line_total_column(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("15.5")
        window._table.item(0, 2).setText("4")
        window._refresh_line_total(0)
        assert window._table.item(0, 3).text() == "$62.00"

    def test_invalid_price_shows_zero(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("n/a")
        window._table.item(0, 2).setText("5")
        window._refresh_line_total(0)
        assert window._table.item(0, 3).text() == "$0.00"


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------


class TestClear:
    def test_clear_removes_all_items(self, window):
        for _ in range(3):
            window._on_add_item()
        window._on_clear()
        assert window._table.rowCount() == 0

    def test_clear_resets_discount_and_tax(self, window):
        window._discount_input.setText("15")
        window._tax_input.setText("7")
        window._on_clear()
        assert window._discount_input.text() == "0"
        assert window._tax_input.text() == "0"

    def test_clear_resets_email(self, window):
        window._email_input.setText("test@example.com")
        window._on_clear()
        assert window._email_input.text() == ""

    def test_clear_resets_labels(self, window):
        window._on_clear()
        assert window._subtotal_label.text() == "Subtotal: $0.00"
        assert window._after_discount_label.text() == "After Discount: $0.00"
        assert window._tax_amount_label.text() == "Tax Amount: $0.00"
        assert window._total_label.text() == "FINAL TOTAL: $0.00"


# ---------------------------------------------------------------------------
# Send Receipt (email validation)
# ---------------------------------------------------------------------------


class TestSendReceipt:
    def test_valid_email_shows_info_message(self, window, monkeypatch):
        called: list[tuple] = []

        def mock_info(parent, title, msg):
            called.append((title, msg))

        monkeypatch.setattr(QMessageBox, "information", mock_info)
        monkeypatch.setattr(QMessageBox, "warning", lambda *a: None)

        window._email_input.setText("user@example.com")
        window._on_send_receipt()
        assert len(called) == 1
        assert called[0][0] == "Receipt Sent"

    def test_invalid_email_shows_warning_message(self, window, monkeypatch):
        called: list[tuple] = []

        def mock_warning(parent, title, msg):
            called.append((title, msg))

        monkeypatch.setattr(QMessageBox, "information", lambda *a: None)
        monkeypatch.setattr(QMessageBox, "warning", mock_warning)

        window._email_input.setText("bad-email")
        window._on_send_receipt()
        assert len(called) == 1
        assert called[0][0] == "Invalid Email"

    def test_empty_email_is_invalid(self, window):
        window._email_input.setText("")
        assert not validate_email(window._email_input.text())


# ---------------------------------------------------------------------------
# Label formatting
# ---------------------------------------------------------------------------


class TestLabels:
    def test_labels_show_formatted_currency_after_calculate(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("2")
        window._discount_input.setText("10")
        window._tax_input.setText("5")
        window._on_calculate()
        assert window._subtotal_label.text() == "Subtotal: $200.00"
        assert window._after_discount_label.text() == "After Discount: $180.00"
        assert window._tax_amount_label.text() == "Tax Amount: $9.00"
        assert window._total_label.text() == "FINAL TOTAL: $189.00"


# ---------------------------------------------------------------------------
# Integration / full flow
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_workflow(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("10")
        window._table.item(0, 2).setText("2")
        window._on_add_item()
        window._table.item(1, 1).setText("5")
        window._table.item(1, 2).setText("3")

        items = window.items()
        assert calculate_total(items) == 35.0

        window._discount_input.setText("10")
        discounted = apply_discount(calculate_total(items), window.discount_percent())
        assert discounted == 31.5

        window._tax_input.setText("8")
        tax = calculate_tax(discounted, window.tax_rate())
        assert tax == 2.52

        assert window.final_total() == 34.02

    def test_cell_change_triggers_recalculation(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("50")
        window._table.item(0, 2).setText("1")
        window._on_calculate()
        assert window.subtotal() == 50.0

    def test_remove_item_updates_totals(self, window):
        window._on_add_item()
        window._table.item(0, 1).setText("100")
        window._table.item(0, 2).setText("1")
        window._on_add_item()
        window._table.item(1, 1).setText("50")
        window._table.item(1, 2).setText("1")

        assert window.subtotal() == 150.0

        window._table.selectRow(0)
        window._on_remove_item()
        assert window.subtotal() == 50.0
