
from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QCheckBox
)
from languages import tr

class AdminPasswordDialog(QDialog):
    def __init__(self, lang: str = "de", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.setWindowTitle(tr("pwd.title", self.lang))
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.edit_new = QLineEdit(); self.edit_new.setEchoMode(QLineEdit.Password)
        self.edit_confirm = QLineEdit(); self.edit_confirm.setEchoMode(QLineEdit.Password)
        self.chk_must_change = QCheckBox("Nutzer muss Passwort beim nächsten Login ändern")
        self.chk_must_change.setChecked(True)

        form.addRow(tr("pwd.new_password", self.lang), self.edit_new)
        form.addRow(tr("pwd.confirm_password", self.lang), self.edit_confirm)
        form.addRow("", self.chk_must_change)
        layout.addLayout(form)

        btns = QHBoxLayout()
        self.btn_change = QPushButton(tr("pwd.change", self.lang))
        self.btn_cancel = QPushButton(tr("pwd.cancel", self.lang))
        btns.addWidget(self.btn_change)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_change.clicked.connect(self._on_change)

    def _on_change(self):
        new = self.edit_new.text().strip()
        confirm = self.edit_confirm.text().strip()
        if new != confirm or len(new) < 6:
            QMessageBox.warning(self, tr("pwd.title", self.lang), tr("pwd.mismatch", self.lang))
            return
        self._new_password = new
        self._must_change = self.chk_must_change.isChecked()
        self.accept()

    def get_values(self):
        return getattr(self, "_new_password", ""), getattr(self, "_must_change", True)
