from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt  # <- wichtig fürs Alignment
from sqlalchemy.orm import sessionmaker
from core.services.auth_service import authenticate
from core.services.settings_service import get_lang, set_lang
from languages import tr
from .registration_dialog import RegistrationDialog


class LoginDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self._lang = get_lang()
        self.setWindowTitle(tr("login.title", self._lang))
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["de", "en", "sr"])
        self.cmb_lang.setCurrentText(self._lang)
        self.ed_user = QLineEdit()
        self.ed_pass = QLineEdit()
        self.ed_pass.setEchoMode(QLineEdit.Password)

        form.addRow(tr("login.language", self._lang), self.cmb_lang)
        form.addRow(tr("login.username", self._lang), self.ed_user)
        form.addRow(tr("login.password", self._lang), self.ed_pass)

        row = QHBoxLayout()
        btn_ok = QPushButton(tr("login.sign_in", self._lang))
        btn_cancel = QPushButton("Cancel" if self._lang == "en" else ("Otkaži" if self._lang == "sr" else "Abbrechen"))
        row.addWidget(btn_ok)
        row.addWidget(btn_cancel)

        layout.addLayout(form)
        layout.addLayout(row)

        # Self-Registration link direkt UNTER dem Login
        # Registrieren-Button mittig unter den Login-Buttons
        btn_reg = QPushButton(tr("login.register_button", self._lang) if tr("login.register_button",
                                                                            self._lang) != "login.register_button" else "Registrieren")
        row_reg = QHBoxLayout()
        row_reg.addStretch(1)
        row_reg.addWidget(btn_reg)
        row_reg.addStretch(1)
        layout.addLayout(row_reg)

        btn_reg.clicked.connect(self._open_register)

        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._do_login)
        self.cmb_lang.currentTextChanged.connect(self._on_lang_change)

    def _on_lang_change(self, lang: str):
        self._lang = lang
        set_lang(lang)
        self.setWindowTitle(tr("login.title", self._lang))
        self.layout().itemAt(0).layout().labelForField(self.cmb_lang).setText(tr("login.language", self._lang))
        self.layout().itemAt(0).layout().labelForField(self.ed_user).setText(tr("login.username", self._lang))
        self.layout().itemAt(0).layout().labelForField(self.ed_pass).setText(tr("login.password", self._lang))

    def _do_login(self):
        user = self.ed_user.text().strip()
        pw = self.ed_pass.text()
        with self.session_factory() as s:
            u = authenticate(s, user, pw)
            if not u:
                self.ed_pass.clear()
                return
            self._user = u
        self.accept()

    def get_current_language(self) -> str:
        return self._lang

    def get_logged_in_user(self):
        return getattr(self, "_user", None)

    def _open_register(self):
        dlg = RegistrationDialog(self.session_factory, lang=self._lang, parent=self)
        if dlg.exec():
            # Benutzername aus dem Registrierungsdialog übernehmen
            try:
                self.ed_user.setText(dlg.get_created_username())
            except Exception:
                pass



