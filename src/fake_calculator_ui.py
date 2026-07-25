"""FakeCalculator - PySide6 UI for financial/purchase calculations."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.calculator import (
    apply_discount,
    calculate_tax,
    calculate_total,
    format_currency,
)
from src.utils import truncate_string, validate_email


class FakeCalculatorWindow(QMainWindow):
    """Main window for the FakeCalculator financial calculator."""

    MAX_ITEM_NAME_LENGTH = 20

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FakeCalculator")
        self.resize(620, 480)
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self._build_items_table(main_layout)
        self._build_item_buttons(main_layout)
        self._build_summary_section(main_layout)
        self._build_email_section(main_layout)
        self._build_action_buttons(main_layout)

    def _build_items_table(self, layout: QVBoxLayout) -> None:
        layout.addWidget(QLabel("Items"))
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Name", "Price ($)", "Quantity", "Line Total"]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table)

    def _build_item_buttons(self, layout: QVBoxLayout) -> None:
        btn_layout = QHBoxLayout()
        self._add_btn = QPushButton("Add Item")
        self._remove_btn = QPushButton("Remove Selected")
        btn_layout.addWidget(self._add_btn)
        btn_layout.addWidget(self._remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _build_summary_section(self, layout: QVBoxLayout) -> None:
        self._subtotal_label = QLabel("Subtotal: $0.00")
        layout.addWidget(self._subtotal_label)

        disc_layout = QHBoxLayout()
        disc_layout.addWidget(QLabel("Discount (%):"))
        self._discount_input = QLineEdit("0")
        self._discount_input.setFixedWidth(80)
        disc_layout.addWidget(self._discount_input)
        disc_layout.addStretch()
        layout.addLayout(disc_layout)

        self._after_discount_label = QLabel("After Discount: $0.00")
        layout.addWidget(self._after_discount_label)

        tax_layout = QHBoxLayout()
        tax_layout.addWidget(QLabel("Tax Rate (%):"))
        self._tax_input = QLineEdit("0")
        self._tax_input.setFixedWidth(80)
        tax_layout.addWidget(self._tax_input)
        tax_layout.addStretch()
        layout.addLayout(tax_layout)

        self._tax_amount_label = QLabel("Tax Amount: $0.00")
        layout.addWidget(self._tax_amount_label)

        self._total_label = QLabel("FINAL TOTAL: $0.00")
        font = self._total_label.font()
        font.setBold(True)
        self._total_label.setFont(font)
        layout.addWidget(self._total_label)

    def _build_email_section(self, layout: QVBoxLayout) -> None:
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("Receipt Email:"))
        self._email_input = QLineEdit()
        self._email_input.setPlaceholderText("user@example.com")
        email_layout.addWidget(self._email_input)
        layout.addLayout(email_layout)

    def _build_action_buttons(self, layout: QVBoxLayout) -> None:
        btn_layout = QHBoxLayout()
        self._calc_btn = QPushButton("Calculate")
        self._clear_btn = QPushButton("Clear")
        self._send_btn = QPushButton("Send Receipt")
        btn_layout.addWidget(self._calc_btn)
        btn_layout.addWidget(self._clear_btn)
        btn_layout.addWidget(self._send_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Signal connections
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._add_btn.clicked.connect(self._on_add_item)
        self._remove_btn.clicked.connect(self._on_remove_item)
        self._calc_btn.clicked.connect(self._on_calculate)
        self._clear_btn.clicked.connect(self._on_clear)
        self._send_btn.clicked.connect(self._on_send_receipt)
        self._table.cellChanged.connect(self._on_cell_changed)
        self._discount_input.textChanged.connect(self._on_calculate)
        self._tax_input.textChanged.connect(self._on_calculate)

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_add_item(self) -> None:
        row = self._table.rowCount()
        self._table.setRowCount(row + 1)
        self._table.blockSignals(True)
        self._table.setItem(row, 0, QTableWidgetItem(""))
        self._table.setItem(row, 1, QTableWidgetItem("0"))
        self._table.setItem(row, 2, QTableWidgetItem("1"))
        line_total_item = QTableWidgetItem("$0.00")
        line_total_item.setFlags(line_total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, 3, line_total_item)
        self._table.blockSignals(False)

    def _on_remove_item(self) -> None:
        selected = self._table.currentRow()
        if selected >= 0:
            self._table.blockSignals(True)
            self._table.removeRow(selected)
            self._table.blockSignals(False)
        self._on_calculate()

    def _on_cell_changed(self, row: int, col: int) -> None:
        if col == 3:
            return
        self._refresh_line_total(row)
        self._on_calculate()

    def _on_calculate(self) -> None:
        items = self._collect_items()
        subtotal = calculate_total(items)

        discount = self._read_discount_percent()
        try:
            after_discount = apply_discount(subtotal, discount)
        except (TypeError, ValueError):
            after_discount = subtotal

        tax_rate = self._read_tax_rate()
        try:
            tax_amount = calculate_tax(after_discount, tax_rate)
        except (TypeError, ValueError):
            tax_amount = 0.0

        total = after_discount + tax_amount

        self._subtotal_label.setText(f"Subtotal: {format_currency(subtotal)}")
        self._after_discount_label.setText(
            f"After Discount: {format_currency(after_discount)}"
        )
        self._tax_amount_label.setText(f"Tax Amount: {format_currency(tax_amount)}")
        self._total_label.setText(f"FINAL TOTAL: {format_currency(total)}")

    def _on_clear(self) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        self._table.blockSignals(False)
        self._discount_input.setText("0")
        self._tax_input.setText("0")
        self._email_input.clear()
        self._subtotal_label.setText("Subtotal: $0.00")
        self._after_discount_label.setText("After Discount: $0.00")
        self._tax_amount_label.setText("Tax Amount: $0.00")
        self._total_label.setText("FINAL TOTAL: $0.00")

    def _on_send_receipt(self) -> None:
        email = self._email_input.text().strip()
        if validate_email(email):
            QMessageBox.information(self, "Receipt Sent", f"Receipt sent to {email}.")
        else:
            QMessageBox.warning(
                self,
                "Invalid Email",
                f"'{truncate_string(email, 40)}' is not a valid email address.",
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_line_total(self, row: int) -> None:
        price_item = self._table.item(row, 1)
        qty_item = self._table.item(row, 2)
        try:
            price = float(price_item.text()) if price_item else 0.0
        except ValueError:
            price = 0.0
        try:
            quantity = int(float(qty_item.text())) if qty_item else 0
        except ValueError:
            quantity = 0
        line_total = price * quantity
        self._table.blockSignals(True)
        self._table.item(row, 3).setText(format_currency(line_total))
        self._table.blockSignals(False)

    def _collect_items(self) -> list[dict]:
        items: list[dict] = []
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 0)
            price_item = self._table.item(row, 1)
            qty_item = self._table.item(row, 2)

            name = name_item.text().strip() if name_item else ""
            name = truncate_string(name, self.MAX_ITEM_NAME_LENGTH)
            try:
                price = float(price_item.text()) if price_item else 0.0
            except ValueError:
                price = 0.0
            try:
                quantity = int(float(qty_item.text())) if qty_item else 0
            except ValueError:
                quantity = 0

            items.append({"name": name, "price": price, "quantity": quantity})
        return items

    def _read_discount_percent(self) -> float:
        text = self._discount_input.text().strip()
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _read_tax_rate(self) -> float:
        text = self._tax_input.text().strip()
        try:
            return float(text)
        except ValueError:
            return 0.0

    # ------------------------------------------------------------------
    # Public API (exposed for testing)
    # ------------------------------------------------------------------

    def items(self) -> list[dict]:
        """Return the current items list (for testing)."""
        return self._collect_items()

    def subtotal(self) -> float:
        """Return the current subtotal (for testing)."""
        return calculate_total(self._collect_items())

    def discount_percent(self) -> float:
        """Return the current discount percent (for testing)."""
        return self._read_discount_percent()

    def tax_rate(self) -> float:
        """Return the current tax rate (for testing)."""
        return self._read_tax_rate()

    def discounted_amount(self) -> float:
        """Return the discounted amount (for testing)."""
        subtotal = self.subtotal()
        try:
            return apply_discount(subtotal, self.discount_percent())
        except (TypeError, ValueError):
            return subtotal

    def tax_amount(self) -> float:
        """Return the tax amount (for testing)."""
        discounted = self.discounted_amount()
        try:
            return calculate_tax(discounted, self.tax_rate())
        except (TypeError, ValueError):
            return 0.0

    def final_total(self) -> float:
        """Return the final total (for testing)."""
        return self.discounted_amount() + self.tax_amount()


def main() -> None:
    """Entry point to run the FakeCalculator application."""
    app = QApplication([])
    window = FakeCalculatorWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
