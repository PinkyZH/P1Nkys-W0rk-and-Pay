from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QCheckBox
)

from languages import tr


class PasswordDialog(QDialog):
    def __init__(self, lang: str = "de", parent=None, admin_mode: bool = False):
        super().__init__(parent)
        self.lang = lang
        self.admin_mode = admin_mode
        self.setWindowTitle(tr("pwd.title", self.lang))
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.edit_new = QLineEdit();
        self.edit_new.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_confirm = QLineEdit();
        self.edit_confirm.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow(tr("pwd.new_password", self.lang), self.edit_new)
        form.addRow(tr("pwd.confirm_password", self.lang), self.edit_confirm)
        layout.addLayout(form)

        if self.admin_mode:
            self.chk_force = QCheckBox(tr("admin_users.pw_force_change", self.lang))
            self.chk_force.setChecked(True)
            layout.addWidget(self.chk_force)
            self.btn_generate = QPushButton(tr("admin_users.generate", self.lang))
            layout.addWidget(self.btn_generate)
            self.btn_generate.clicked.connect(self._on_generate)

        btns = QHBoxLayout()
        self.btn_change = QPushButton(tr("pwd.change", self.lang))
        self.btn_cancel = QPushButton(tr("pwd.cancel", self.lang))
        btns.addWidget(self.btn_change);
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.btn_change.clicked.connect(self._on_change)
        self.btn_cancel.clicked.connect(self.reject)

    def _on_generate(self):
        import secrets, string
        alphabet = string.ascii_letters + string.digits
        pw = ''.join(secrets.choice(alphabet) for _ in range(12))
        self.edit_new.setText(pw);
        self.edit_confirm.setText(pw)

    def _on_change(self):
        new = self.edit_new.text().strip()
        conf = self.edit_confirm.text().strip()
        if new != conf:
            QMessageBox.warning(self, tr("pwd.title", self.lang), tr("pwd.mismatch", self.lang));
            return
        if len(new) < 6:
            QMessageBox.warning(self, tr("pwd.title", self.lang),
                                "Min. 6 Zeichen erforderlich." if self.lang == "de" else "Min. 6 characters required.");
            return
        self.accept()

    def get_new_password(self) -> str:
        return self.edit_new.text().strip()

    def get_force_change(self) -> bool:
        return getattr(self, "chk_force", None).isChecked() if self.admin_mode else False
