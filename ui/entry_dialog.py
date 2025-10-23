from __future__ import annotations
from typing import Optional
from datetime import date, time
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QInputDialog
)
from PySide6.QtCore import QDate, QTime
from sqlalchemy.orm import sessionmaker
from languages import tr
from core.services.work_service import create_entry, update_entry
from core.models import WorkEntry

# ------------------------------------------------------------
# ERWEITERTE Typenliste (inkl. Arzttermin, Spital + Custom)
# ------------------------------------------------------------
ENTRY_TYPES = [
    ("WORK","work"),
    ("VACATION","vacation"),
    ("SICK","sick"),
    ("HOLIDAY","holiday"),
    ("OFF","off"),
    ("APPOINTMENT","appointment"),   # Arzttermin
    ("HOSPITAL","hospital"),         # Spital
    ("CUSTOM","custom_entry_label")  # Benutzerdefiniert...
]

# Fallback-Wörterbuch (falls languages.py keine calendar.* Keys hat)
_CAL_FALLBACK = {
    "de": {
        "title_new": "Neuer Eintrag", "title_edit": "Eintrag bearbeiten",
        "date": "Datum", "start": "Beginn", "end": "Ende",
        "break": "Pause (Min)", "hours": "Stunden", "type": "Typ", "note": "Notiz",
        "wage_override": "Std.-Lohn (Override)", "overtime": "Überstunden", "location": "Ort",
        "save": "Speichern", "cancel": "Abbrechen", "validation_date": "Bitte ein gültiges Datum wählen.",
        "entry_types": {
            "work":"Arbeit","vacation":"Urlaub","sick":"Krank","holiday":"Feiertag","off":"Frei","other":"Sonstiges",
            "appointment":"Arzttermin","hospital":"Spital","custom_entry_label":"Benutzerdefiniert…"
        },
    },
    "en": {
        "title_new": "New Entry", "title_edit": "Edit Entry",
        "date": "Date", "start": "Start", "end": "End",
        "break": "Break (min)", "hours": "Hours", "type": "Type", "note": "Note",
        "wage_override": "Hourly override", "overtime": "Overtime", "location": "Location",
        "save": "Save", "cancel": "Cancel", "validation_date": "Please choose a valid date.",
        "entry_types": {
            "work":"Work","vacation":"Vacation","sick":"Sick","holiday":"Holiday","off":"Off","other":"Other",
            "appointment":"Appointment","hospital":"Hospital","custom_entry_label":"Custom..."
        },
    },
    "sr": {
        "title_new": "Novi unos", "title_edit": "Izmena unosa",
        "date": "Datum", "start": "Početak", "end": "Kraj",
        "break": "Pauza (min)", "hours": "Sati", "type": "Tip", "note": "Beleška",
        "wage_override": "Satnica (override)", "overtime": "Prekovremeni", "location": "Lokacija",
        "save": "Sačuvaj", "cancel": "Otkaži", "validation_date": "Izaberi važeći datum.",
        "entry_types": {
            "work":"Rad","vacation":"Odmor","sick":"Bolovanje","holiday":"Praznik","off":"Slobodno","other":"Ostalo",
            "appointment":"Pregled","hospital":"Bolnica","custom_entry_label":"Prilagođeno..."
        },
    },
}

def _t(lang: str, key: str) -> str:
    full = f"calendar.{key}"
    val = tr(full, lang)
    return _CAL_FALLBACK.get(lang, _CAL_FALLBACK["de"]).get(key, key) if val == full else val

def qdate_to_date(qd: QDate) -> Optional[date]:
    if not qd or not qd.isValid():
        return None
    return qd.toPython()

def qtime_to_time(qt: QTime) -> Optional[time]:
    if not qt or not qt.isValid():
        return None
    return time(hour=qt.hour(), minute=qt.minute())

class EntryDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, user_id: int, lang: str="de",
                 entry: Optional[WorkEntry]=None, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.user_id = user_id
        self.lang = lang
        self.entry = entry
        self.setWindowTitle(_t(self.lang, "title_edit" if entry else "title_new"))
        self.setSizeGripEnabled(True)
        self._build(); self.adjustSize()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_date = QDateEdit(); self.ed_date.setCalendarPopup(True)
        self.ed_start = QTimeEdit(); self.ed_end = QTimeEdit()
        self.ed_break = QSpinBox(); self.ed_break.setRange(0, 600); self.ed_break.setSuffix(" min")
        self.ed_hours = QDoubleSpinBox(); self.ed_hours.setRange(0.0, 24.0); self.ed_hours.setDecimals(2); self.ed_hours.setSingleStep(0.25)

        # Typen-Combo (mit Fallback)
        self.ed_type = QComboBox()
        types_map = _CAL_FALLBACK.get(self.lang, _CAL_FALLBACK["de"])["entry_types"]
        for key, kind in ENTRY_TYPES:
            label = tr(f"calendar.entry_types.{kind}", self.lang)
            if label == f"calendar.entry_types.{kind}":
                label = types_map[kind]
            self.ed_type.addItem(label, key)

        self.ed_note = QLineEdit()
        self.ed_wage = QDoubleSpinBox(); self.ed_wage.setRange(0.0, 1000.0); self.ed_wage.setDecimals(2)
        self.ed_overtime = QDoubleSpinBox(); self.ed_overtime.setRange(0.0, 24.0); self.ed_overtime.setDecimals(2)
        self.ed_location = QLineEdit()

        form.addRow(_t(self.lang,"date"), self.ed_date)
        form.addRow(_t(self.lang,"start"), self.ed_start)
        form.addRow(_t(self.lang,"end"), self.ed_end)
        form.addRow(_t(self.lang,"break"), self.ed_break)
        form.addRow(_t(self.lang,"hours"), self.ed_hours)
        form.addRow(_t(self.lang,"type"), self.ed_type)
        form.addRow(_t(self.lang,"note"), self.ed_note)
        form.addRow(_t(self.lang,"wage_override"), self.ed_wage)
        form.addRow(_t(self.lang,"overtime"), self.ed_overtime)
        form.addRow(_t(self.lang,"location"), self.ed_location)
        layout.addLayout(form)

        row = QHBoxLayout()
        btn_save = QPushButton(_t(self.lang,"save"))
        btn_cancel = QPushButton(_t(self.lang,"cancel"))
        row.addWidget(btn_save); row.addWidget(btn_cancel)
        layout.addLayout(row)

        btn_save.clicked.connect(self._save)
        btn_cancel.clicked.connect(self.reject)

        # ► richtige Signatur: Klassenmethode, außerhalb von _build definiert
        self.ed_type.currentIndexChanged.connect(self._on_type_changed)

        # Standardwerte bei "Neu"
        if not self.entry:
            from PySide6.QtCore import QTime, QDate
            self.ed_date.setDate(QDate.currentDate())
            self.ed_start.setTime(QTime(7, 0))
            self.ed_end.setTime(QTime(16, 30))
            self.ed_break.setValue(90)

        if self.entry:
            self._load()

    # ----------------- EVENTS -----------------
    def _on_type_changed(self, idx: int):
        code = self.ed_type.itemData(idx)
        if code == "CUSTOM":
            text, ok = QInputDialog.getText(self, "Neuer Typ", "Bezeichnung für den Typ:")
            if ok and text.strip():
                label = text.strip()
                # Code als „CUSTOM:<label>“ speichern
                self.ed_type.setItemText(idx, label)
                self.ed_type.setItemData(idx, f"CUSTOM:{label}")
            else:
                # zurück auf WORK
                self.ed_type.setCurrentIndex(0)

    # ----------------- LOAD / SAVE -----------------
    def _load(self):
        e = self.entry
        self.ed_date.setDate(QDate(e.date.year, e.date.month, e.date.day))
        if e.start_time: self.ed_start.setTime(QTime(e.start_time.hour, e.start_time.minute))
        if e.end_time: self.ed_end.setTime(QTime(e.end_time.hour, e.end_time.minute))
        if e.break_minutes is not None: self.ed_break.setValue(int(e.break_minutes))
        if e.hours is not None: self.ed_hours.setValue(float(e.hours))
        # Auswahl per Code (auch CUSTOM:<...> wird korrekt gesetzt)
        want = e.entry_type or "WORK"
        for i in range(self.ed_type.count()):
            if self.ed_type.itemData(i) == want:
                self.ed_type.setCurrentIndex(i); break
        self.ed_note.setText(e.note or "")
        if e.hourly_override is not None: self.ed_wage.setValue(float(e.hourly_override))
        if e.overtime_hours is not None: self.ed_overtime.setValue(float(e.overtime_hours))
        self.ed_location.setText(e.location or "")

    def _save(self):
        data = {
            "date": qdate_to_date(self.ed_date.date()),
            "start_time": qtime_to_time(self.ed_start.time()),
            "end_time": qtime_to_time(self.ed_end.time()),
            "break_minutes": int(self.ed_break.value()),
            "hours": float(self.ed_hours.value()) if self.ed_hours.value() > 0 else None,
            "entry_type": self.ed_type.currentData(),
            "note": self.ed_note.text().strip(),
            "hourly_override": float(self.ed_wage.value()) if self.ed_wage.value() > 0 else None,
            "overtime_hours": float(self.ed_overtime.value()) if self.ed_overtime.value() > 0 else None,
            "location": self.ed_location.text().strip() or None,
        }
        if not data["date"]:
            QMessageBox.warning(self, _t(self.lang, "title_new"), _t(self.lang, "validation_date"))
            return
        with self.session_factory() as s:
            try:
                if self.entry:
                    update_entry(s, self.entry.id, **data)
                else:
                    create_entry(s, self.user_id, **data)
            except Exception as ex:
                QMessageBox.critical(self, _t(self.lang, "title_new"), f"Error: {ex}")
                return
        self.accept()
