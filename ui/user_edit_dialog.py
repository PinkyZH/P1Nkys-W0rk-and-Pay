from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox, QFormLayout,
    QLineEdit, QDateEdit, QComboBox, QPushButton, QHBoxLayout, QDoubleSpinBox, QMessageBox, QCheckBox, QFileDialog
)
from PySide6.QtCore import QDate
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from languages import tr, LANG
from core.models import User, UserProfile

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
        self.setWindowTitle(tr("admin_edit.title", self.lang))
        self.setSizeGripEnabled(True)
        self._avatar_tmp: Optional[str] = None
        self._build()
        self._load()
        self.adjustSize()

    def _build(self):
        root = QVBoxLayout(self)
        grid = QGridLayout(); root.addLayout(grid)

        # Spalte 1 – Benutzer
        box_user = QGroupBox("Benutzerdaten")
        f1 = QFormLayout(box_user)
        self.ed_username = QLineEdit()
        self.cb_role = QComboBox(); self.cb_role.addItems(["USER","HR","ADMIN"])
        self.cb_active = QCheckBox(tr("admin_edit.active", self.lang))
        self.btn_avatar_choose = QPushButton(tr("profile.choose_file", self.lang))
        self.btn_avatar_remove = QPushButton(tr("profile.remove", self.lang))

        self.ed_first = QLineEdit(); self.ed_last = QLineEdit()
        self.date_birthday = QDateEdit(); self.date_birthday.setCalendarPopup(True)
        self.cb_civil = QComboBox()
        cmap = LANG.get(self.lang, LANG["de"]).get("choices", {}).get("civil_status", {
            "single":"Ledig","married":"Verheiratet","separated":"Getrennt","divorced":"Geschieden","widowed":"Verwitwet"
        })
        for key, label in cmap.items(): self.cb_civil.addItem(label, key)
        self.ed_permit = QLineEdit()
        self.ed_ahv = QLineEdit()  # AHV-Nr.

        f1.addRow(tr("admin_users.username", self.lang), self.ed_username)
        f1.addRow(tr("admin_edit.role", self.lang), self.cb_role)
        f1.addRow(tr("admin_edit.active", self.lang), self.cb_active)
        f1.addRow(tr("profile.avatar", self.lang) if tr("profile.avatar", self.lang) != "profile.avatar" else "Avatar", self.btn_avatar_choose)
        f1.addRow("", self.btn_avatar_remove)
        f1.addRow(tr("admin_users.first_name", self.lang), self.ed_first)
        f1.addRow(tr("admin_users.last_name", self.lang), self.ed_last)
        f1.addRow(tr("admin_users.birthday", self.lang), self.date_birthday)
        f1.addRow(tr("profile.civil_status", self.lang), self.cb_civil)
        f1.addRow(tr("profile.permit_status", self.lang), self.ed_permit)
        f1.addRow(tr("profile.ahv_number", self.lang) if tr("profile.ahv_number", self.lang) != "profile.ahv_number" else "AHV-Nr.", self.ed_ahv)
        grid.addWidget(box_user, 0, 0)

        # Spalte 2 – Adresse
        box_addr = QGroupBox("Adresse & Kontakt")
        f2 = QFormLayout(box_addr)
        self.combo_locale = QComboBox(); self.combo_locale.addItems(["de","en","sr"])
        self.ed_region = QLineEdit(); self.ed_address = QLineEdit()
        self.ed_postcode = QLineEdit(); self.ed_city = QLineEdit()
        self.ed_email = QLineEdit(); self.ed_phone = QLineEdit()
        f2.addRow(tr("profile.locale", self.lang), self.combo_locale)
        f2.addRow(tr("profile.region_code", self.lang), self.ed_region)
        f2.addRow(tr("profile.address", self.lang), self.ed_address)
        f2.addRow(tr("profile.postcode", self.lang), self.ed_postcode)
        f2.addRow(tr("profile.city", self.lang), self.ed_city)
        f2.addRow(tr("profile.email", self.lang), self.ed_email)
        f2.addRow(tr("profile.phone", self.lang), self.ed_phone)
        grid.addWidget(box_addr, 0, 1)

        # Spalte 3 – Bank & Lohn
        box_bank = QGroupBox("Bank & Lohn")
        f3 = QFormLayout(box_bank)
        self.ed_bank_name = QLineEdit(); self.ed_bank_addr = QLineEdit()
        self.ed_bank_zip = QLineEdit(); self.ed_bank_city = QLineEdit(); self.ed_bank_country = QLineEdit()
        self.ed_account_no = QLineEdit(); self.ed_iban = QLineEdit()
        self.sp_hourly = QDoubleSpinBox(); self.sp_hourly.setRange(0, 1000); self.sp_hourly.setDecimals(2)
        f3.addRow(tr("profile.bank_name", self.lang), self.ed_bank_name)
        f3.addRow(tr("profile.bank_address", self.lang), self.ed_bank_addr)
        f3.addRow(tr("profile.bank_zip", self.lang), self.ed_bank_zip)
        f3.addRow(tr("profile.bank_city", self.lang), self.ed_bank_city)
        f3.addRow(tr("profile.bank_country", self.lang), self.ed_bank_country)
        f3.addRow(tr("profile.account_number", self.lang), self.ed_account_no)
        f3.addRow(tr("profile.iban", self.lang), self.ed_iban)
        f3.addRow(tr("profile.hourly_wage", self.lang) if tr("profile.hourly_wage", self.lang) != "profile.hourly_wage" else "Stundenlohn", self.sp_hourly)
        grid.addWidget(box_bank, 0, 2)

        # Spalte 4 – Anstellung
        box_emp = QGroupBox("Anstellung")
        f4 = QFormLayout(box_emp)
        self.ed_emp_id = QLineEdit()     # Mitarbeiter-ID
        self.ed_emp_code = QLineEdit()   # Kürzel
        self.ed_employer = QLineEdit()   # Arbeitgeber
        self.date_employed = QDateEdit(); self.date_employed.setCalendarPopup(True)
        f4.addRow(tr("profile.employee_id", self.lang) if tr("profile.employee_id", self.lang) != "profile.employee_id" else "Mitarbeiter-ID", self.ed_emp_id)
        f4.addRow(tr("profile.employee_code", self.lang) if tr("profile.employee_code", self.lang) != "profile.employee_code" else "Kürzel", self.ed_emp_code)
        f4.addRow(tr("profile.employer", self.lang) if tr("profile.employer", self.lang) != "profile.employer" else "Arbeitgeber", self.ed_employer)
        f4.addRow(tr("profile.employment_start", self.lang) if tr("profile.employment_start", self.lang) != "profile.employment_start" else "Eintrittsdatum", self.date_employed)
        grid.addWidget(box_emp, 0, 3)

        # Buttons
        row = QHBoxLayout()
        btn_save = QPushButton(tr("admin_edit.save", self.lang)); btn_cancel = QPushButton(tr("admin_edit.cancel", self.lang))
        row.addStretch(1); row.addWidget(btn_save); row.addWidget(btn_cancel); root.addLayout(row)
        btn_save.clicked.connect(self._save); btn_cancel.clicked.connect(self.reject)
        self.btn_avatar_choose.clicked.connect(self._choose_avatar); self.btn_avatar_remove.clicked.connect(self._remove_avatar)

    def _choose_avatar(self):
        fn, _ = QFileDialog.getOpenFileName(self, tr("profile.choose_file", self.lang), "", "Images (*.png *.jpg *.jpeg)")
        if fn: self._avatar_tmp = fn
    def _remove_avatar(self): self._avatar_tmp = "__REMOVE__"

    def _load(self):
        with self.session_factory() as s:
            u = s.execute(select(User).where(User.id == self.user_id)).scalar_one_or_none()
            p = s.execute(select(UserProfile).where(UserProfile.user_id == self.user_id)).scalar_one_or_none()
            if p is None:
                p = UserProfile(user_id=self.user_id); s.add(p); s.commit()

        # Benutzer
        self.ed_username.setText(u.username if u else ""); self.cb_role.setCurrentText((u.role or "USER").upper() if u else "USER")
        active = getattr(u, "is_active", True); self.cb_active.setChecked(bool(active))

        # Person
        def _select_by_data(combo: QComboBox, key: Optional[str]):
            if key is None: return
            for i in range(combo.count()):
                if combo.itemData(i) == key: combo.setCurrentIndex(i); break

        self.ed_first.setText(p.first_name or ""); self.ed_last.setText(p.last_name or "")
        if p.birthday: self.date_birthday.setDate(QDate(p.birthday.year, p.birthday.month, p.birthday.day))
        _select_by_data(self.cb_civil, p.civil_status or None)
        self.ed_permit.setText(p.permit_status or "")

        # Kontakt
        self.combo_locale.setCurrentText(p.locale or "de")
        self.ed_region.setText(p.region_code or ""); self.ed_address.setText(p.address or "")
        self.ed_postcode.setText(p.postcode or ""); self.ed_city.setText(p.city or "")
        self.ed_email.setText(p.email or ""); self.ed_phone.setText(p.phone or "")

        # AHV + Lohn
        self.ed_ahv.setText(getattr(p, "ahv_number", None) or "")
        self.sp_hourly.setValue(float(p.hourly_brutto or 0.0))

        # Bank
        self.ed_bank_name.setText(p.bank_name or ""); self.ed_bank_addr.setText(p.bank_address or "")
        self.ed_bank_zip.setText(p.bank_zip or ""); self.ed_bank_city.setText(p.bank_city or "")
        self.ed_bank_country.setText(p.bank_country or ""); self.ed_account_no.setText(p.account_number or "")
        self.ed_iban.setText(p.iban or "")

        # Anstellung
        self.ed_emp_id.setText(p.employee_id or ""); self.ed_emp_code.setText(p.employee_code or "")
        self.ed_employer.setText(p.employer or "")
        if p.employment_start:
            self.date_employed.setDate(QDate(p.employment_start.year, p.employment_start.month, p.employment_start.day))

    def _save(self):
        with self.session_factory() as s:
            u = s.execute(select(User).where(User.id == self.user_id)).scalar_one_or_none()
            if u:
                u.role = self.cb_role.currentText().upper()
                if hasattr(u, "is_active"): u.is_active = self.cb_active.isChecked()

            p = s.execute(select(UserProfile).where(UserProfile.user_id == self.user_id)).scalar_one_or_none()
            if p is None:
                p = UserProfile(user_id=self.user_id); s.add(p)

            def _txt(w: QLineEdit):
                t = w.text().strip()
                return t or None

            p.first_name = _txt(self.ed_first); p.last_name  = _txt(self.ed_last)
            d = self.date_birthday.date(); p.birthday = d.toPython() if d and d.isValid() else None
            p.civil_status = self.cb_civil.currentData(); p.permit_status = _txt(self.ed_permit)
            p.locale = self.combo_locale.currentText(); p.region_code = _txt(self.ed_region)
            p.address = _txt(self.ed_address); p.postcode = _txt(self.ed_postcode)
            p.city = _txt(self.ed_city); p.email = _txt(self.ed_email); p.phone = _txt(self.ed_phone)

            # AHV + Lohn
            p.ahv_number = _txt(self.ed_ahv); p.hourly_brutto = float(self.sp_hourly.value())

            # Bank
            p.bank_name = _txt(self.ed_bank_name); p.bank_address = _txt(self.ed_bank_addr)
            p.bank_zip = _txt(self.ed_bank_zip); p.bank_city = _txt(self.ed_bank_city)
            p.bank_country = _txt(self.ed_bank_country); p.account_number = _txt(self.ed_account_no)
            p.iban = _txt(self.ed_iban)

            # Anstellung
            p.employee_id = _txt(self.ed_emp_id); p.employee_code = _txt(self.ed_emp_code)
            p.employer = _txt(self.ed_employer)
            de = self.date_employed.date(); p.employment_start = de.toPython() if de and de.isValid() else None

            s.commit()
        QMessageBox.information(self, tr("admin_edit.title", self.lang), tr("profile.saved", self.lang))
        self.accept()
