from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QDateEdit, QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QInputDialog
from PySide6.QtCore import QDate
from sqlalchemy.orm import sessionmaker
from languages import tr
from core.services.absence_service import submit_absence

# Codes -> werden gespeichert
ABSENCE_CODES = ["VACATION","SICK","HOLIDAY","OFF","APPOINTMENT","HOSPITAL","CUSTOM"]

# Anzeigenamen (fallback, falls languages.py die Keys noch nicht hat)
_ABS_FALLBACK = {
    "de": {"VACATION":"Urlaub","SICK":"Krank","HOLIDAY":"Feiertag","OFF":"Frei","APPOINTMENT":"Arzttermin","HOSPITAL":"Spital","CUSTOM":"Benutzerdefiniert…"},
    "en": {"VACATION":"Vacation","SICK":"Sick","HOLIDAY":"Holiday","OFF":"Off","APPOINTMENT":"Appointment","HOSPITAL":"Hospital","CUSTOM":"Custom…"},
    "sr": {"VACATION":"Odmor","SICK":"Bolovanje","HOLIDAY":"Praznik","OFF":"Slobodno","APPOINTMENT":"Pregled","HOSPITAL":"Bolnica","CUSTOM":"Prilagođeno…"},
}

def _t(lang: str, key: str, default: str) -> str:
    val = tr(key, lang)
    return default if val == key else val

class AbsenceRequestDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, user_id: int, lang: str="de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user_id = user_id
        self.lang = lang
        self.setWindowTitle(_t(self.lang, "abs.title", "Abwesenheit beantragen"))
        self.setSizeGripEnabled(True)
        self._build(); self.adjustSize()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.combo_type = QComboBox()
        for code in ABSENCE_CODES:
            # Übersetzter Anzeigename, Code als itemData
            label = tr(f"abs.types.{code.lower()}", self.lang)
            if label == f"abs.types.{code.lower()}":
                label = _ABS_FALLBACK.get(self.lang, _ABS_FALLBACK["de"]).get(code, code)
            self.combo_type.addItem(label, code)

        self.edit_label = QLineEdit(); self.edit_label.setPlaceholderText(_t(self.lang, "abs.custom_placeholder", "Custom-Label (nur bei Benutzerdefiniert)"))
        self.date_from = QDateEdit(); self.date_from.setCalendarPopup(True); self.date_from.setDate(QDate.currentDate())
        self.date_to   = QDateEdit(); self.date_to.setCalendarPopup(True); self.date_to.setDate(QDate.currentDate())
        self.edit_reason = QLineEdit()

        form.addRow(_t(self.lang, "abs.type", "Typ"), self.combo_type)
        form.addRow(_t(self.lang, "abs.custom_label", "Custom-Label"), self.edit_label)
        form.addRow(_t(self.lang, "abs.from", "Von"), self.date_from)
        form.addRow(_t(self.lang, "abs.to", "Bis"), self.date_to)
        form.addRow(_t(self.lang, "abs.reason", "Grund"), self.edit_reason)
        layout.addLayout(form)

        row = QHBoxLayout()
        btn_ok = QPushButton(_t(self.lang, "abs.send", "Antrag senden"))
        btn_cancel = QPushButton(_t(self.lang, "abs.cancel", "Abbrechen"))
        row.addWidget(btn_ok); row.addWidget(btn_cancel)
        layout.addLayout(row)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._submit)

        # Wenn CUSTOM gewählt wird und kein Custom-Label gesetzt ist → Nachfrage
        self.combo_type.currentIndexChanged.connect(self._maybe_ask_custom)

    def _maybe_ask_custom(self, *_):
        code = self.combo_type.currentData()
        if code == "CUSTOM" and not self.edit_label.text().strip():
            text, ok = QInputDialog.getText(self, _t(self.lang, "abs.custom_title", "Benutzerdefinierter Typ"),
                                            _t(self.lang, "abs.custom_prompt", "Bezeichnung:"))
            if ok and text.strip():
                self.edit_label.setText(text.strip())

    def _submit(self):
        code = self.combo_type.currentData()
        label = self.edit_label.text().strip() or None
        d1 = self.date_from.date().toPython()
        d2 = self.date_to.date().toPython()
        reason = self.edit_reason.text().strip()
        try:
            with self.session_factory() as s:
                submit_absence(s, self.user_id, code, d1, d2, reason=reason, custom_label=label)
            QMessageBox.information(self, _t(self.lang, "abs.title", "Abwesenheit beantragen"),
                                    _t(self.lang, "abs.ok", "Antrag eingereicht."))
            self.accept()
        except Exception as ex:
            QMessageBox.critical(self, _t(self.lang, "abs.title", "Abwesenheit beantragen"), str(ex))
