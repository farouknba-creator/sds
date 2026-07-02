"""
Suppliers tab - full CRUD for the supplier / legal-entity database.

This is the only tab fully built out in Phase 1. The user can:
  - Add a new supplier
  - Edit an existing supplier (including address, contact, logo path)
  - Delete a supplier
  - Pick a logo file via file dialog
  - Preview the logo
  - Save back to config/suppliers.yaml
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.paths import ASSETS_DIR, resolve_path
from ..core.supplier import Address, Supplier, SupplierDB


class SuppliersTab(QWidget):
    def __init__(self, db: SupplierDB, status_cb=None):
        super().__init__()
        self.db = db
        self.status_cb = status_cb or (lambda msg: None)
        self._editing_id: str | None = None
        self._build_ui()
        self._refresh_table()

    # ---- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        # Top: list of suppliers
        outer.addWidget(QLabel("Stored legal entities (select one to edit, or click New):"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Legal Name", "DBA"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_select)
        outer.addWidget(self.table)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_new = QPushButton("New")
        self.btn_save = QPushButton("Save")
        self.btn_delete = QPushButton("Delete")
        self.btn_new.clicked.connect(self._on_new)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch()
        outer.addLayout(btn_row)

        # Form
        outer.addWidget(QLabel("Details:"))
        form_widget = QWidget()
        self.form = QFormLayout(form_widget)
        form.setLabelAlignment(Qt.AlignRight)

        self.in_id = QLineEdit()
        self.in_id.setPlaceholderText("auto-generated if blank")
        self.in_legal_name = QLineEdit()
        self.in_dba = QLineEdit()
        self.in_street = QLineEdit()
        self.in_street2 = QLineEdit()
        self.in_city = QLineEdit()
        self.in_state = QLineEdit()
        self.in_postal = QLineEdit()
        self.in_country = QLineEdit()
        self.in_phone = QLineEdit()
        self.in_emergency = QLineEdit()
        self.in_website = QLineEdit()
        self.in_email = QLineEdit()
        self.in_regulatory = QLineEdit()

        # Logo row with picker + preview
        logo_row = QHBoxLayout()
        self.in_logo = QLineEdit()
        self.in_logo.setPlaceholderText("assets/logos/your_logo.png")
        self.btn_pick_logo = QPushButton("Browse...")
        self.btn_pick_logo.clicked.connect(self._on_pick_logo)
        logo_row.addWidget(self.in_logo, 1)
        logo_row.addWidget(self.btn_pick_logo)
        self.logo_preview = QLabel("No logo")
        self.logo_preview.setFixedSize(120, 50)
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setStyleSheet("border: 1px solid #ccc; background: #fafafa;")
        logo_row.addWidget(self.logo_preview)
        logo_widget = QWidget()
        logo_widget.setLayout(logo_row)

        self.form.addRow("ID:", self.in_id)
        self.form.addRow("Legal Name *:", self.in_legal_name)
        self.form.addRow("DBA:", self.in_dba)
        self.form.addRow("Street:", self.in_street)
        self.form.addRow("Street 2:", self.in_street2)
        self.form.addRow("City:", self.in_city)
        self.form.addRow("State/Region:", self.in_state)
        self.form.addRow("Postal Code:", self.in_postal)
        self.form.addRow("Country:", self.in_country)
        self.form.addRow("Phone:", self.in_phone)
        self.form.addRow("Emergency Phone:", self.in_emergency)
        self.form.addRow("Website:", self.in_website)
        self.form.addRow("Email:", self.in_email)
        self.form.addRow("Regulatory Contact:", self.in_regulatory)
        self.form.addRow("Logo Path:", logo_widget)

        outer.addWidget(form_widget)
        outer.addStretch()

        self._clear_form()

    # ---- Data ops --------------------------------------------------------
    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        for s in self.db.suppliers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(s.id))
            self.table.setItem(row, 1, QTableWidgetItem(s.legal_name))
            self.table.setItem(row, 2, QTableWidgetItem(s.dba))

    def _clear_form(self) -> None:
        self._editing_id = None
        for w in (self.in_id, self.in_legal_name, self.in_dba, self.in_street,
                  self.in_street2, self.in_city, self.in_state, self.in_postal,
                  self.in_country, self.in_phone, self.in_emergency,
                  self.in_website, self.in_email, self.in_regulatory, self.in_logo):
            w.clear()
        self.logo_preview.setPixmap(QPixmap())
        self.logo_preview.setText("No logo")

    def _load_into_form(self, s: Supplier) -> None:
        self._editing_id = s.id
        self.in_id.setText(s.id)
        self.in_legal_name.setText(s.legal_name)
        self.in_dba.setText(s.dba)
        self.in_street.setText(s.address.street)
        self.in_street2.setText(s.address.street2)
        self.in_city.setText(s.address.city)
        self.in_state.setText(s.address.state)
        self.in_postal.setText(s.address.postal_code)
        self.in_country.setText(s.address.country)
        self.in_phone.setText(s.phone)
        self.in_emergency.setText(s.emergency_phone)
        self.in_website.setText(s.website)
        self.in_email.setText(s.email)
        self.in_regulatory.setText(s.regulatory_contact)
        self.in_logo.setText(s.logo_path)
        self._update_logo_preview(s.logo_path)

    def _collect_from_form(self) -> Supplier:
        sid = self.in_id.text().strip()
        legal = self.in_legal_name.text().strip()
        if not legal:
            raise ValueError("Legal Name is required")
        addr = Address(
            street=self.in_street.text().strip(),
            street2=self.in_street2.text().strip(),
            city=self.in_city.text().strip(),
            state=self.in_state.text().strip(),
            postal_code=self.in_postal.text().strip(),
            country=self.in_country.text().strip(),
        )
        return Supplier(
            id=sid,
            legal_name=legal,
            dba=self.in_dba.text().strip(),
            address=addr,
            phone=self.in_phone.text().strip(),
            emergency_phone=self.in_emergency.text().strip(),
            website=self.in_website.text().strip(),
            email=self.in_email.text().strip(),
            regulatory_contact=self.in_regulatory.text().strip(),
            logo_path=self.in_logo.text().strip(),
        )

    # ---- Slots -----------------------------------------------------------
    def _on_select(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        row = items[0].row()
        sid = self.table.item(row, 0).text()
        s = self.db.get(sid)
        if s:
            self._load_into_form(s)

    def _on_new(self) -> None:
        self._clear_form()
        self.in_legal_name.setFocus()

    def _on_save(self) -> None:
        try:
            s = self._collect_from_form()
        except ValueError as e:
            QMessageBox.warning(self, "Validation", str(e))
            return
        try:
            if self._editing_id and self.db.get(self._editing_id):
                # Preserve original ID
                s.id = self._editing_id
                self.db.update(s)
            else:
                self.db.add(s)
                self._editing_id = s.id
        except ValueError as e:
            QMessageBox.warning(self, "Save failed", str(e))
            return
        self._refresh_table()
        self.status_cb(f"Saved supplier: {s.legal_name}")

    def _on_delete(self) -> None:
        if not self._editing_id:
            return
        confirm = QMessageBox.question(
            self, "Delete supplier",
            f"Delete supplier '{self._editing_id}'? This cannot be undone.",
        )
        if confirm != QMessageBox.Yes:
            return
        self.db.remove(self._editing_id)
        self._clear_form()
        self._refresh_table()
        self.status_cb("Supplier deleted")

    def _on_pick_logo(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        start_dir = str(ASSETS_DIR / "logos") if (ASSETS_DIR / "logos").exists() else str(ASSETS_DIR)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select logo", start_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All files (*.*)",
        )
        if not path:
            return
        # Copy into assets/logos/ if user picked a file elsewhere
        src = Path(path)
        target_dir = ASSETS_DIR / "logos"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / src.name
        if src.resolve() != target.resolve():
            try:
                target.write_bytes(src.read_bytes())
            except OSError as e:
                QMessageBox.warning(self, "Copy failed", str(e))
                return
        rel = f"assets/logos/{src.name}"
        self.in_logo.setText(rel)
        self._update_logo_preview(rel)

    def _update_logo_preview(self, logo_path: str) -> None:
        if not logo_path:
            self.logo_preview.setPixmap(QPixmap())
            self.logo_preview.setText("No logo")
            return
        p = resolve_path(logo_path)
        if not p.exists():
            self.logo_preview.setText("Not found")
            self.logo_preview.setPixmap(QPixmap())
            return
        pix = QPixmap(str(p))
        if pix.isNull():
            self.logo_preview.setText("Invalid image")
            return
        self.logo_preview.setPixmap(pix.scaled(
            120, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation,
        ))
        self.logo_preview.setText("")
