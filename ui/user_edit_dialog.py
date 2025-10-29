from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox, QFormLayout,
    QLineEdit, QDateEdit, QComboBox, QPushButton, QHBoxLayout, QDoubleSpinBox, QMessageBox, QCheckBox, QFileDialog
)
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from core.models import User, UserProfile
from core.services.auth_service import hash_password
from core.utils.i18n import t as _t
from languages import tr, LANG


def T(key: str, lang: str, fallback: str) -> str:
    """Übersetze key; wenn die Sprache den key nicht kennt, nimm fallback."""
    v = _t(key, lang)
    return v if v != key else fallback


class UserEditDialog(QDialog):
    """
    Admin: Benutzer bearbeiten – 4 Spalten
      [Benutzerdaten] | [Adresse/Kontakt] | [Bank & Lohn] | [Anstellung]
    - AHV-Nr. + Stundenlohn editierbar
    """

    def __init__(self, session_factory: sessionmaker, user_id: int, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user_id = user_id
        self.lang = lang
        self.setWindowTitle(tr("admin_users.title", self.lang) if tr("admin_users.title",
                                                                     self.lang) != "admin_users.title" else "Benutzerverwaltung")
        self.setSizeGripEnabled(True)
        self._avatar_tmp: Optional[str] = None
        self._build()
        self._load()
        self.adjustSize()
        self.setSizeGripEnabled(True)  # manuelles Resizing bleibt möglich
        self.resize(max(self.sizeHint().width(), 1484),  # mind. ~980px Startbreite
                    self.sizeHint().height())

    def _build(self):
        root = QVBoxLayout(self)
        grid = QGridLayout()
        root.addLayout(grid)

        # ---------------- Spalte 1 – Benutzer ----------------
        box_user = QGroupBox(T("admin_edit.group_user", self.lang, "Benutzerdaten"))
        f1 = QFormLayout(box_user)

        self.ed_username = QLineEdit()
        self.cb_role = QComboBox()
        self.cb_role.addItems(["USER", "HR", "ADMIN"])

        # Checkbox bekommt ihren Text selbst; links im FormLayout kein Label
        self.cb_active = QCheckBox(T("admin_edit.active", self.lang, "Aktiv"))

        self.btn_avatar_choose = QPushButton(T("profile.choose_file", self.lang, "Datei wählen"))
        self.btn_avatar_remove = QPushButton(T("profile.remove", self.lang, "Entfernen"))

        self.ed_first = QLineEdit()
        self.ed_last = QLineEdit()
        self.date_birthday = QDateEdit()
        self.date_birthday.setCalendarPopup(True)

        self.cb_civil = QComboBox()
        cmap = LANG.get(self.lang, LANG["de"]).get("choices", {}).get(
            "civil_status",
            {"single": "Ledig", "married": "Verheiratet", "separated": "Getrennt", "divorced": "Geschieden",
             "widowed": "Verwitwet"}
        )
        for key, label in cmap.items():
            self.cb_civil.addItem(label, key)

        self.ed_permit = QLineEdit()
        self.ed_ahv = QLineEdit()  # AHV-Nr.

        f1.addRow(T("admin_users.username", self.lang, "Benutzername"), self.ed_username)
        f1.addRow(T("admin_edit.role", self.lang, "Rolle"), self.cb_role)
        f1.addRow("", self.cb_active)  # <— kein linkes Label mehr
        f1.addRow(T("profile.avatar", self.lang, "Avatar"), self.btn_avatar_choose)
        f1.addRow("", self.btn_avatar_remove)
        f1.addRow(T("admin_users.first_name", self.lang, "Vorname"), self.ed_first)
        f1.addRow(T("admin_users.last_name", self.lang, "Nachname"), self.ed_last)
        f1.addRow(T("admin_users.birthday", self.lang, "Geburtstag"), self.date_birthday)
        f1.addRow(T("profile.civil_status", self.lang, "Zivilstand"), self.cb_civil)
        f1.addRow(T("profile.permit_status", self.lang, "Aufenthaltsstatus"), self.ed_permit)
        f1.addRow(T("profile.ahv_number", self.lang, "AHV-Nr."), self.ed_ahv)
        grid.addWidget(box_user, 0, 0)

        # ---------------- Spalte 2 – Adresse & Kontakt ----------------
        box_addr = QGroupBox(T("admin_edit.group_contact", self.lang, "Adresse  Kontakt"))
        f2 = QFormLayout(box_addr)
        self.combo_locale = QComboBox()
        self.combo_locale.addItems(["de", "en", "sr"])
        self.ed_region = QLineEdit()
        self.ed_address = QLineEdit()
        self.ed_postcode = QLineEdit()
        self.ed_city = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_phone = QLineEdit()

        f2.addRow(T("profile.locale", self.lang, "Sprache"), self.combo_locale)
        f2.addRow(T("profile.region_code", self.lang, "Region/Kanton"), self.ed_region)
        f2.addRow(T("profile.address", self.lang, "Adresse"), self.ed_address)
        f2.addRow(T("profile.postcode", self.lang, "Postleitzahl"), self.ed_postcode)
        f2.addRow(T("profile.city", self.lang, "Ort"), self.ed_city)
        f2.addRow(T("profile.email", self.lang, "E-Mail"), self.ed_email)
        f2.addRow(T("profile.phone", self.lang, "Telefon"), self.ed_phone)
        grid.addWidget(box_addr, 0, 1)

        # ---------------- Spalte 3 – Bank & Lohn ----------------
        box_bank = QGroupBox(T("admin_edit.group_wage", self.lang, "Bank  Lohn"))
        f3 = QFormLayout(box_bank)
        self.ed_bank_name = QLineEdit()
        self.ed_bank_addr = QLineEdit()
        self.ed_bank_zip = QLineEdit()
        self.ed_bank_city = QLineEdit()
        self.ed_bank_country = QLineEdit()
        self.ed_account_no = QLineEdit()
        self.ed_iban = QLineEdit()

        self.sp_hourly = QDoubleSpinBox()
        self.sp_hourly.setRange(0, 1000)
        self.sp_hourly.setDecimals(2)

        f3.addRow(T("profile.bank_name", self.lang, "Name der Bank"), self.ed_bank_name)
        f3.addRow(T("profile.bank_address", self.lang, "Adresse der Bank"), self.ed_bank_addr)
        f3.addRow(T("profile.bank_zip", self.lang, "Postleitzahl der Bank"), self.ed_bank_zip)
        f3.addRow(T("profile.bank_city", self.lang, "Ort der Bank"), self.ed_bank_city)
        f3.addRow(T("profile.bank_country", self.lang, "Land der Bank"), self.ed_bank_country)
        f3.addRow(T("profile.account_number", self.lang, "Kontonummer"), self.ed_account_no)
        f3.addRow(T("profile.iban", self.lang, "IBAN"), self.ed_iban)
        f3.addRow(T("profile.hourly_wage", self.lang, "Stundenlohn"), self.sp_hourly)
        grid.addWidget(box_bank, 0, 2)

        # ---------------- Spalte 4 – Anstellung ----------------
        box_emp = QGroupBox(T("admin_edit.group_employment", self.lang, "Anstellung"))
        f4 = QFormLayout(box_emp)
        self.ed_emp_id = QLineEdit()
        self.ed_emp_code = QLineEdit()
        self.ed_employer = QLineEdit()
        self.date_employed = QDateEdit()
        self.date_employed.setCalendarPopup(True)

        f4.addRow(T("profile.employee_id", self.lang, "Mitarbeiter-ID"), self.ed_emp_id)
        f4.addRow(T("profile.employee_code", self.lang, "Kürzel"), self.ed_emp_code)
        f4.addRow(T("profile.employer", self.lang, "Arbeitgeber"), self.ed_employer)
        f4.addRow(T("profile.employment_start", self.lang, "Eintrittsdatum"), self.date_employed)
        grid.addWidget(box_emp, 0, 3)

        # ---------------- Buttons ----------------
        row = QHBoxLayout()
        btn_save = QPushButton(T("admin_edit.save", self.lang, "Speichern"))
        btn_cancel = QPushButton(T("admin_edit.cancel", self.lang, "Abbrechen"))
        row.addStretch(1)
        row.addWidget(btn_save)
        row.addWidget(btn_cancel)
        root.addLayout(row)

        btn_save.clicked.connect(self._save)
        btn_cancel.clicked.connect(self.reject)
        self.btn_avatar_choose.clicked.connect(self._choose_avatar)
        self.btn_avatar_remove.clicked.connect(self._remove_avatar)

    def _choose_avatar(self):
        fn, _ = QFileDialog.getOpenFileName(self, tr("profile.choose_file", self.lang), "",
                                            "Images (*.png *.jpg *.jpeg)")
        if fn: self._avatar_tmp = fn

    def _remove_avatar(self):
        self._avatar_tmp = "__REMOVE__"

    def _load(self):
        """
        Füllt die Maske. Bei user_id=None (Neu) KEIN DB-Insert!
        """
        # Neu-Modus -> nur Defaults in die Felder, keine DB-Operation
        if self.user_id is None:
            # sinnvolle Defaults
            try:
                self.cmb_role.setCurrentText("USER")
            except Exception:
                pass
            try:
                self.chk_active.setChecked(True)
            except Exception:
                pass
            try:
                # Sprache/Locale auf 'de'
                if hasattr(self, "cmb_locale"):
                    self.cmb_locale.setCurrentText("de")
            except Exception:
                pass
            # numerische Felder o.ä. kannst du hier ebenfalls vorbelegen
            return

        # Edit-Modus -> Daten laden und in Felder schreiben
        with self.session_factory() as s:
            u = s.get(User, self.user_id)
            if not u:
                QMessageBox.warning(self, "Fehler", f"Benutzer {self.user_id} nicht gefunden.")
                return

            # Profil ermitteln (NICHT erstellen)
            p = s.execute(
                select(UserProfile).where(UserProfile.user_id == self.user_id)
            ).scalars().first()

            # --- Benutzerdaten in UI ---
            if hasattr(self, "ed_username"): self.ed_username.setText(u.username or "")
            if hasattr(self, "cmb_role"): self.cmb_role.setCurrentText((u.role or "").upper())
            if hasattr(self, "chk_active"): self.chk_active.setChecked(getattr(u, "is_active", True))

            # --- Profildaten in UI (nur wenn vorhanden) ---
            if p:
                if hasattr(self, "cmb_locale") and (p.locale or ""):
                    self.cmb_locale.setCurrentText(p.locale)
                if hasattr(self, "ed_first"): self.ed_first.setText(p.first_name or "")
                if hasattr(self, "ed_last"): self.ed_last.setText(p.last_name or "")
                if hasattr(self, "ed_phone"): self.ed_phone.setText(p.phone or "")
                if hasattr(self, "ed_email"): self.ed_email.setText(p.email or "")
                if hasattr(self, "ed_address"): self.ed_address.setText(p.address or "")
                if hasattr(self, "ed_postcode"): self.ed_postcode.setText((p.postal_code or ""))
                if hasattr(self, "ed_city"): self.ed_city.setText(p.city or "")
                if hasattr(self, "ed_employer"): self.ed_employer.setText(p.employer or "")
                if hasattr(self, "ed_employee_id"): self.ed_employee_id.setText(p.employee_id or "")
                if hasattr(self, "ed_ahv"): self.ed_ahv.setText(p.ahv_number or "")
                # weitere Felder analog …

    def _save(self):
        """
        Speichert Benutzer + Profil.
        - Neu: erst User anlegen, ID übernehmen, dann Profil anlegen.
        - Edit: vorhandene Datensätze aktualisieren; Profil ggf. anlegen.
        """
        # Werte aus UI
        username = (self.ed_username.text() if hasattr(self, "ed_username") else "").strip()
        role = (self.cmb_role.currentText() if hasattr(self, "cmb_role") else "USER") or "USER"
        is_active = bool(self.chk_active.isChecked()) if hasattr(self, "chk_active") else True
        locale = (self.cmb_locale.currentText() if hasattr(self, "cmb_locale") else "de") or "de"

        first = (self.ed_first.text() if hasattr(self, "ed_first") else "").strip()
        last = (self.ed_last.text() if hasattr(self, "ed_last") else "").strip()
        phone = (self.ed_phone.text() if hasattr(self, "ed_phone") else "").strip()
        email = (self.ed_email.text() if hasattr(self, "ed_email") else "").strip()
        address = (self.ed_address.text() if hasattr(self, "ed_address") else "").strip()
        postal_code = (self.ed_postcode.text() if hasattr(self, "ed_postcode") else "").strip()
        city = (self.ed_city.text() if hasattr(self, "ed_city") else "").strip()
        employer = (self.ed_employer.text() if hasattr(self, "ed_employer") else "").strip()
        employee_id = (self.ed_employee_id.text() if hasattr(self, "ed_employee_id") else "").strip()
        ahv = (self.ed_ahv.text() if hasattr(self, "ed_ahv") else "").strip()

        if not username:
            QMessageBox.warning(self, "Fehler", "Benutzername darf nicht leer sein.")
            return

        with self.session_factory() as s:
            # --- Neu anlegen ---
            if self.user_id is None:
                # einfachen Default setzen; bei Bedarf Dialog für Passwort bauen
                default_pwd = "ChangeMe123"
                u = User(username=username, role=role, is_active=is_active, password_hash=hash_password(default_pwd))
                s.add(u)
                s.flush()  # erzeugt ID
                self.user_id = u.id

                # Profil anlegen
                p = UserProfile(
                    user_id=self.user_id,
                    locale=locale,
                    first_name=first, last_name=last,
                    phone=phone, email=email,
                    address=address, postal_code=postal_code, city=city,
                    employer=employer, employee_id=employee_id,
                    ahv_number=ahv,
                )
                s.add(p)
                s.commit()
                QMessageBox.information(self, "OK", "Benutzer erstellt.")
                self.accept()
                return

            # --- Update vorhandener Datensätze ---
            u = s.get(User, self.user_id)
            if not u:
                QMessageBox.warning(self, "Fehler", f"Benutzer {self.user_id} nicht gefunden.")
                return
            u.username = username
            u.role = role
            u.is_active = is_active
            s.add(u)

            # Profil holen/ggf. anlegen
            p = s.execute(select(UserProfile).where(UserProfile.user_id == self.user_id)).scalars().first()
            if not p:
                p = UserProfile(user_id=self.user_id)
            p.locale = locale
            p.first_name = first
            p.last_name = last
            p.phone = phone
            p.email = email
            p.address = address
            p.postal_code = postal_code
            p.city = city
            p.employer = employer
            p.employee_id = employee_id
            p.ahv_number = ahv

            s.add(p)
            s.commit()
            QMessageBox.information(self, "OK", "Änderungen gespeichert.")
            self.accept()
