from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QFormLayout,
    QLabel, QLineEdit, QDateEdit, QComboBox, QPushButton, QCheckBox,
    QFileDialog, QMessageBox, QDoubleSpinBox
)
from PySide6.QtCore import QDate, Qt
    # Avatar-Vorschau
from PySide6.QtGui import QPixmap
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from languages import tr, LANG
from core.models import User, UserProfile
from ui.window_flags import apply_window_controls
from core.services.log_service import log_activity, log_error


def qdate_to_date(qd: QDate):
    if not qd or not qd.isValid():
        return None
    return qd.toPython()


class ProfileDialog(QDialog):
    """
    Profil in 4 Spalten:
      [Persönlich] | [Adresse/Kontakt] | [Bank & Lohn] | [Anstellung (Admin)]
    - AHV-Nr. unter Aufenthaltstatus
    - Stundenlohn (User & Admin) bei Bankdaten (ein-/ausblendbar)
    - Admin-Felder (Mitarbeiter-ID, Kürzel, Arbeitgeber, Eintrittsdatum) in Spalte 4
    """
    def __init__(self, session_factory: sessionmaker, user_id: int, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user_id = user_id
        self.lang = lang
        self.setWindowTitle(tr("profile.title", self.lang))
        self.setSizeGripEnabled(True)

        # Rolle bestimmen
        with self.session_factory() as s:
            u = s.execute(select(User).where(User.id == self.user_id)).scalar_one_or_none()
            self._is_admin = bool(u and (u.role or "").upper() == "ADMIN")

        self._avatar_tmp: Optional[str] = None
        self._remove_avatar_flag = False

        self._build()
        self._load()
        self.adjustSize()

    # ---------- UI ----------
    def _build(self):
        apply_window_controls(self)
        root = QVBoxLayout(self)

        # Avatar-Zeile
        av_row = QHBoxLayout()
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(96, 96)
        self.btn_choose_avatar = QPushButton(tr("profile.choose_file", self.lang))
        self.btn_remove_avatar = QPushButton(tr("profile.remove", self.lang))
        av_row.addWidget(self.lbl_avatar)
        av_row.addWidget(self.btn_choose_avatar)
        av_row.addWidget(self.btn_remove_avatar)
        root.addLayout(av_row)

        grid = QGridLayout()
        root.addLayout(grid)

        # Spalte 1 – Persönlich
        box_pers = QGroupBox("Persönlich")
        f1 = QFormLayout(box_pers)

        self.combo_gender = QComboBox()
        gmap = LANG.get(self.lang, LANG["de"]).get("choices", {}).get(
            "gender", {"male": "Männlich", "female": "Weiblich"}
        )
        for key, label in gmap.items():
            self.combo_gender.addItem(label, key)

        self.edit_first_name = QLineEdit()
        self.edit_last_name = QLineEdit()
        self.date_birthday = QDateEdit()
        self.date_birthday.setCalendarPopup(True)

        self.combo_civil = QComboBox()
        cmap = LANG.get(self.lang, LANG["de"]).get("choices", {}).get(
            "civil_status",
            {
                "single": "Ledig",
                "married": "Verheiratet",
                "separated": "Getrennt",
                "divorced": "Geschieden",
                "widowed": "Verwitwet",
            },
        )
        for key, label in cmap.items():
            self.combo_civil.addItem(label, key)

        self.edit_permit = QLineEdit()  # Aufenthaltsstatus
        self.edit_ahv = QLineEdit()     # AHV-Nr.

        f1.addRow(tr("profile.gender", self.lang), self.combo_gender)
        f1.addRow(tr("profile.first_name", self.lang), self.edit_first_name)
        f1.addRow(tr("profile.last_name", self.lang), self.edit_last_name)
        f1.addRow(tr("profile.birthday", self.lang), self.date_birthday)
        f1.addRow(tr("profile.civil_status", self.lang), self.combo_civil)
        f1.addRow(tr("profile.permit_status", self.lang), self.edit_permit)
        f1.addRow(
            tr("profile.ahv_number", self.lang)
            if tr("profile.ahv_number", self.lang) != "profile.ahv_number"
            else "AHV-Nr.",
            self.edit_ahv,
        )
        grid.addWidget(box_pers, 0, 0)

        # Spalte 2 – Adresse/Kontakt
        box_addr = QGroupBox("Adresse & Kontakt")
        f2 = QFormLayout(box_addr)

        self.combo_locale = QComboBox()
        self.combo_locale.addItems(["de", "en", "sr"])
        self.edit_region = QLineEdit()
        self.edit_address = QLineEdit()
        self.edit_postcode = QLineEdit()
        self.edit_city = QLineEdit()
        self.edit_email = QLineEdit()
        self.edit_phone = QLineEdit()

        f2.addRow(tr("profile.locale", self.lang), self.combo_locale)
        f2.addRow(tr("profile.region_code", self.lang), self.edit_region)
        f2.addRow(tr("profile.address", self.lang), self.edit_address)
        f2.addRow(tr("profile.postcode", self.lang), self.edit_postcode)
        f2.addRow(tr("profile.city", self.lang), self.edit_city)
        f2.addRow(tr("profile.email", self.lang), self.edit_email)
        f2.addRow(tr("profile.phone", self.lang), self.edit_phone)

        grid.addWidget(box_addr, 0, 1)

        # Spalte 3 – Bank & Lohn
        box_bank = QGroupBox("Bank & Lohn")
        f3 = QFormLayout(box_bank)

        self.chk_bank_visible = QCheckBox(tr("profile.show_bank", self.lang))
        f3.addRow(self.chk_bank_visible)

        self.edit_bank_name = QLineEdit()
        self.edit_bank_address = QLineEdit()
        self.edit_bank_zip = QLineEdit()
        self.edit_bank_city = QLineEdit()
        self.edit_bank_country = QLineEdit()
        self.edit_account_number = QLineEdit()
        self.edit_iban = QLineEdit()

        f3.addRow(tr("profile.bank_name", self.lang), self.edit_bank_name)
        f3.addRow(tr("profile.bank_address", self.lang), self.edit_bank_address)
        f3.addRow(tr("profile.bank_zip", self.lang), self.edit_bank_zip)
        f3.addRow(tr("profile.bank_city", self.lang), self.edit_bank_city)
        f3.addRow(tr("profile.bank_country", self.lang), self.edit_bank_country)
        f3.addRow(tr("profile.account_number", self.lang), self.edit_account_number)
        f3.addRow(tr("profile.iban", self.lang), self.edit_iban)

        # Stundenlohn
        self.sp_hourly = QDoubleSpinBox()
        self.sp_hourly.setRange(0, 1000)
        self.sp_hourly.setDecimals(2)
        f3.addRow(
            tr("profile.hourly_wage", self.lang)
            if tr("profile.hourly_wage", self.lang) != "profile.hourly_wage"
            else "Stundenlohn",
            self.sp_hourly,
        )

        grid.addWidget(box_bank, 0, 2)

        # Spalte 4 – Anstellung (Admin)
        box_admin = QGroupBox("Anstellung (Admin)")
        f4 = QFormLayout(box_admin)
        self.edit_emp_id = QLineEdit()     # Mitarbeiter-ID
        self.edit_emp_code = QLineEdit()   # Kürzel
        self.edit_employer = QLineEdit()   # Arbeitgeber
        self.date_employed = QDateEdit()   # Eintritt
        self.date_employed.setCalendarPopup(True)

        f4.addRow(
            tr("profile.employee_id", self.lang)
            if tr("profile.employee_id", self.lang) != "profile.employee_id"
            else "Mitarbeiter-ID",
            self.edit_emp_id,
        )
        f4.addRow(
            tr("profile.employee_code", self.lang)
            if tr("profile.employee_code", self.lang) != "profile.employee_code"
            else "Kürzel",
            self.edit_emp_code,
        )
        f4.addRow(
            tr("profile.employer", self.lang)
            if tr("profile.employer", self.lang) != "profile.employer"
            else "Arbeitgeber",
            self.edit_employer,
        )
        f4.addRow(
            tr("profile.employment_start", self.lang)
            if tr("profile.employment_start", self.lang) != "profile.employment_start"
            else "Eintrittsdatum",
            self.date_employed,
        )

        grid.addWidget(box_admin, 0, 3)

        # Buttons
        row_btn = QHBoxLayout()
        self.btn_save = QPushButton(tr("profile.save", self.lang))
        self.btn_cancel = QPushButton(tr("profile.cancel", self.lang))
        row_btn.addStretch(1)
        row_btn.addWidget(self.btn_save)
        row_btn.addWidget(self.btn_cancel)
        root.addLayout(row_btn)

        # Events
        self.btn_choose_avatar.clicked.connect(self._choose_avatar)
        self.btn_remove_avatar.clicked.connect(self._remove_avatar)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save)
        self.chk_bank_visible.toggled.connect(self._apply_bank_visibility)

        # Nur Admin darf die Admin-Felder bearbeiten – die übrigen Felder sind für alle frei
        for w in (self.edit_emp_id, self.edit_emp_code, self.edit_employer, self.date_employed):
            w.setEnabled(self._is_admin)

    # ---------- LOAD ----------
    def _load(self):
        with self.session_factory() as s:
            p = s.execute(select(UserProfile).where(UserProfile.user_id == self.user_id)).scalar_one_or_none()
            if p is None:
                p = UserProfile(user_id=self.user_id)
                s.add(p)
                s.commit()

        # Helper
        def _select_by_data(combo: QComboBox, key: Optional[str]):
            if key is None:
                return
            for i in range(combo.count()):
                if combo.itemData(i) == key:
                    combo.setCurrentIndex(i)
                    break

        # Persönlich
        _select_by_data(self.combo_gender, p.gender or None)
        self.edit_first_name.setText(p.first_name or "")
        self.edit_last_name.setText(p.last_name or "")
        if p.birthday:
            self.date_birthday.setDate(QDate(p.birthday.year, p.birthday.month, p.birthday.day))
        _select_by_data(self.combo_civil, p.civil_status or None)
        self.edit_permit.setText(p.permit_status or "")
        self.edit_ahv.setText(getattr(p, "ahv_number", None) or "")

        # Kontakt
        self.combo_locale.setCurrentText(p.locale or "de")
        self.edit_region.setText(p.region_code or "")
        self.edit_address.setText(p.address or "")
        self.edit_postcode.setText(p.postcode or "")
        self.edit_city.setText(p.city or "")
        self.edit_email.setText(p.email or "")
        self.edit_phone.setText(p.phone or "")
        self.edit_iban.setText(p.iban or "")

        # Avatar
        if p.avatar_path:
            try:
                self.lbl_avatar.setPixmap(
                    QPixmap(p.avatar_path).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            except Exception:
                self.lbl_avatar.setPixmap(QPixmap())

        # Bank-Block sichtbar
        self.chk_bank_visible.setChecked(True)
        self._apply_bank_visibility()

        # Lohn
        self.sp_hourly.setValue(float(getattr(p, "hourly_brutto", 0.0) or 0.0))

        # Anstellung (Admin)
        self.edit_emp_id.setText(p.employee_id or "")
        self.edit_emp_code.setText(p.employee_code or "")
        self.edit_employer.setText(p.employer or "")
        if p.employment_start:
            self.date_employed.setDate(QDate(p.employment_start.year, p.employment_start.month, p.employment_start.day))

        # Wichtige Änderung:
        # Für Nicht-Admin NICHTS global deaktivieren – nur die Admin-Gruppe ist read-only.
        # (Damit normale User ihre persönlichen/Adress-/Bankdaten selbst pflegen können.)

    # ---------- SAVE ----------
    def _save(self):
        try:
            with self.session_factory() as s:
                p = s.execute(select(UserProfile).where(UserProfile.user_id == self.user_id)).scalar_one_or_none()
                if p is None:
                    p = UserProfile(user_id=self.user_id)
                    s.add(p)

                # Immer speichern: alle persönlichen/Adress-/Bank-Felder (User & Admin)
                def _txt(w: QLineEdit):
                    t = w.text().strip()
                    return t or None

                # Persönlich
                p.gender = self.combo_gender.currentData()
                p.first_name = _txt(self.edit_first_name)
                p.last_name  = _txt(self.edit_last_name)
                d = self.date_birthday.date()
                p.birthday = d.toPython() if d and d.isValid() else None
                p.civil_status = self.combo_civil.currentData()
                p.permit_status = _txt(self.edit_permit)
                p.ahv_number = _txt(self.edit_ahv)

                # Kontakt
                p.locale = self.combo_locale.currentText()
                p.region_code = _txt(self.edit_region)
                p.address = _txt(self.edit_address)
                p.postcode = _txt(self.edit_postcode)
                p.city = _txt(self.edit_city)
                p.email = _txt(self.edit_email)
                p.phone = _txt(self.edit_phone)
                p.iban = _txt(self.edit_iban)

                # Bank/Lohn
                p.hourly_brutto = float(self.sp_hourly.value())

                # Admin-Felder nur, wenn Admin
                if self._is_admin:
                    p.employee_id = _txt(self.edit_emp_id)
                    p.employee_code = _txt(self.edit_emp_code)
                    p.employer = _txt(self.edit_employer)
                    de = self.date_employed.date()
                    p.employment_start = de.toPython() if de and de.isValid() else None

                s.commit()
                log_activity(self.user_id, "profile.save", {"changed": True})

            QMessageBox.information(self, tr("profile.title", self.lang),
                                    tr("dialogs.common.saved", self.lang))

            self.accept()

        except Exception as ex:
            QMessageBox.critical(self, "profile.save", str(ex))
            log_error("Fehler beim Speichern von Änderungen im Profil", exc=ex)

    # ---------- Helpers ----------
    def _apply_bank_visibility(self):
        vis = self.chk_bank_visible.isChecked()
        for w in (
            self.edit_bank_name,
            self.edit_bank_address,
            self.edit_bank_zip,
            self.edit_bank_city,
            self.edit_bank_country,
            self.edit_account_number,
            self.edit_iban,
        ):
            w.setVisible(vis)

    def _choose_avatar(self):
        fn, _ = QFileDialog.getOpenFileName(
            self, tr("profile.choose_file", self.lang), "", "Images (*.png *.jpg *.jpeg)"
        )
        if fn:
            self._avatar_tmp = fn
            self._remove_avatar_flag = False
            self.lbl_avatar.setPixmap(
                QPixmap(fn).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def _remove_avatar(self):
        self._avatar_tmp = None
        self._remove_avatar_flag = True
        self.lbl_avatar.setPixmap(QPixmap())
