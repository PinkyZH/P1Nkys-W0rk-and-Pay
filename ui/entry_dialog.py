from __future__ import annotations
from typing import Optional
from datetime import date, time

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QInputDialog, QWidget
)
from PySide6.QtCore import QDate, QTime, Qt

from sqlalchemy.orm import sessionmaker
from languages import tr
from core.services.work_service import create_entry, update_entry
from core.models import WorkEntry

# ------------------------------
# Hilfen
# ------------------------------
_CAL_FALLBACK = {
    "de": {
        "title_new": "Neuer Eintrag", "title_edit": "Eintrag bearbeiten",
        "date": "Datum", "start": "Beginn", "end": "Ende",
        "break": "Pause (Min)", "hours": "Stunden", "type": "Typ", "note": "Notiz",
        "wage_override": "Std.-Lohn (Override)", "overtime": "Überstunden", "location": "Ort",
        "save": "Speichern", "cancel": "Abbrechen", "validation_date": "Bitte ein gültiges Datum wählen.",
        "entry_types": {
            "work":"Arbeit","off":"Frei","holiday":"Feiertag","vacation":"Urlaub",
            "sick":"Krank","accident":"Unfall","appointment":"Arzttermin","hospital":"Spital",
            "custom_entry_label":"Benutzerdefiniert…"
        },
        "pay_override":"Bezahlung", "pay_custom":"Benutzerdefiniert (Faktor 0–2)"
    },
    "en": {
        "title_new": "New Entry", "title_edit": "Edit Entry",
        "date": "Date", "start": "Start", "end": "End",
        "break": "Break (min)", "hours": "Hours", "type": "Type", "note": "Note",
        "wage_override": "Hourly override", "overtime": "Overtime", "location": "Location",
        "save": "Save", "cancel": "Cancel", "validation_date": "Please choose a valid date.",
        "entry_types": {
            "work":"Work","off":"Off","holiday":"Holiday","vacation":"Vacation",
            "sick":"Sick","accident":"Accident","appointment":"Appointment","hospital":"Hospital",
            "custom_entry_label":"Custom…"
        },
        "pay_override":"Payment", "pay_custom":"Custom (factor 0–2)"
    },
    "sr": {
        "title_new": "Novi unos", "title_edit": "Izmena unosa",
        "date": "Datum", "start": "Početak", "end": "Kraj",
        "break": "Pauza (min)", "hours": "Sati", "type": "Tip", "note": "Beleška",
        "wage_override": "Satnica (override)", "overtime": "Prekovremeni", "location": "Lokacija",
        "save": "Sačuvaj", "cancel": "Otkaži", "validation_date": "Izaberi važeći datum.",
        "entry_types": {
            "work":"Rad","off":"Slobodno","holiday":"Praznik","vacation":"Odmor",
            "sick":"Bolovanje","accident":"Nezgoda","appointment":"Pregled","hospital":"Bolnica",
            "custom_entry_label":"Prilagođeno…"
        },
        "pay_override":"Plaćanje", "pay_custom":"Prilagođeno (faktor 0–2)"
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


# Reihenfolge der Typen (dein Wunsch)
TYPE_ORDER = [
    "WORK",
    "OFF",
    "HOLIDAY",
    "VACATION",
    "SICK",
    "ACCIDENT",
    "APPOINTMENT",
    "HOSPITAL",
    "CUSTOM",
]

# Abbildung Typcode -> key im i18n-Fallback
TYPE_KEYMAP = {
    "WORK":"work", "OFF":"off", "HOLIDAY":"holiday", "VACATION":"vacation",
    "SICK":"sick", "ACCIDENT":"accident", "APPOINTMENT":"appointment", "HOSPITAL":"hospital",
    "CUSTOM":"custom_entry_label"
}


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
        self._build()
        self.adjustSize()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Datum/Zeit
        self.ed_date = QDateEdit(); self.ed_date.setCalendarPopup(True)
        self.ed_start = QTimeEdit(); self.ed_end = QTimeEdit()
        self.ed_break = QSpinBox(); self.ed_break.setRange(0, 600); self.ed_break.setSuffix(" min")

        # Stunden + Typ
        self.ed_hours = QDoubleSpinBox(); self.ed_hours.setRange(0.0, 24.0); self.ed_hours.setDecimals(2); self.ed_hours.setSingleStep(0.25)
        self.ed_type = QComboBox()

        # Typen einfügen (in gewünschter Reihenfolge)
        types_map = _CAL_FALLBACK.get(self.lang, _CAL_FALLBACK["de"])["entry_types"]
        self.ed_type.clear()
        for code in TYPE_ORDER:
            key = TYPE_KEYMAP[code]
            label = tr(f"calendar.entry_types.{key}", self.lang)
            if label == f"calendar.entry_types.{key}":
                label = types_map[key]
            self.ed_type.addItem(label, code)

        # weitere Felder
        self.ed_note = QLineEdit()
        self.ed_wage = QDoubleSpinBox(); self.ed_wage.setRange(0.0, 1000.0); self.ed_wage.setDecimals(2)
        self.ed_overtime = QDoubleSpinBox(); self.ed_overtime.setRange(0.0, 24.0); self.ed_overtime.setDecimals(2)
        self.ed_location = QLineEdit()

        # Bezahlung-Override
        self.cmb_pay = QComboBox()
        for label, val in [("100%",1.0),("90%",0.9),("80%",0.8),("70%",0.7),("60%",0.6),("50%",0.5),("Unbezahlt",0.0),("Benutzerdefiniert…",-2.0)]:
            self.cmb_pay.addItem(label, val)
        self.sp_pay_custom = QDoubleSpinBox()
        self.sp_pay_custom.setRange(0.0, 2.0); self.sp_pay_custom.setDecimals(2); self.sp_pay_custom.setValue(1.0)
        self.sp_pay_custom.setEnabled(False)

        def _on_pay_changed():
            self.sp_pay_custom.setEnabled(self.cmb_pay.currentData() == -2.0)
        self.cmb_pay.currentIndexChanged.connect(_on_pay_changed)

        # Formular zusammenbauen
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
        form.addRow(_CAL_FALLBACK[self.lang]["pay_override"], self.cmb_pay)
        form.addRow(_CAL_FALLBACK[self.lang]["pay_custom"], self.sp_pay_custom)

        layout.addLayout(form)

        # Buttons
        row = QHBoxLayout()
        btn_save = QPushButton(_t(self.lang,"save"))
        btn_cancel = QPushButton(_t(self.lang,"cancel"))
        row.addStretch(1); row.addWidget(btn_save); row.addWidget(btn_cancel)
        layout.addLayout(row)

        btn_save.clicked.connect(self._save)
        btn_cancel.clicked.connect(self.reject)
        self.ed_type.currentIndexChanged.connect(self._on_type_changed)

        # Standardwerte bei "Neu"
        if not self.entry:
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
            text, ok = QInputDialog.getText(self, _CAL_FALLBACK[self.lang]["entry_types"]["custom_entry_label"],
                                            _CAL_FALLBACK[self.lang]["entry_types"]["custom_entry_label"])
            if ok and text.strip():
                label = text.strip()
                self.ed_type.setItemText(idx, label)
                self.ed_type.setItemData(idx, f"CUSTOM:{label}")
            else:
                self.ed_type.setCurrentIndex(0)

    # ----------------- LOAD / SAVE -----------------
    def _load(self):
        e = self.entry
        self.ed_date.setDate(QDate(e.date.year, e.date.month, e.date.day))
        if e.start_time: self.ed_start.setTime(QTime(e.start_time.hour, e.start_time.minute))
        if e.end_time: self.ed_end.setTime(QTime(e.end_time.hour, e.end_time.minute))
        if e.break_minutes is not None: self.ed_break.setValue(int(e.break_minutes))
        if e.hours is not None: self.ed_hours.setValue(float(e.hours))

        # Typ setzen (auch CUSTOM:<...>)
        want = e.entry_type or "WORK"
        for i in range(self.ed_type.count()):
            if self.ed_type.itemData(i) == want:
                self.ed_type.setCurrentIndex(i); break

        self.ed_note.setText(e.note or "")
        self.ed_location.setText(e.location or "")
        if hasattr(e, "hourly_override") and e.hourly_override is not None:
            self.ed_wage.setValue(float(e.hourly_override))
        if hasattr(e, "overtime_hours") and e.overtime_hours is not None:
            self.ed_overtime.setValue(float(e.overtime_hours))

        # Pay-Override laden
        rate = getattr(e, "pay_rate_override", None)
        if rate is None:
            self.cmb_pay.setCurrentIndex(0)  # 100%
        else:
            # exakte Wahl?
            found = False
            for i in range(self.cmb_pay.count()):
                if self.cmb_pay.itemData(i) == rate:
                    self.cmb_pay.setCurrentIndex(i); found = True; break
            if not found:
                # custom
                for i in range(self.cmb_pay.count()):
                    if self.cmb_pay.itemData(i) == -2.0:
                        self.cmb_pay.setCurrentIndex(i)
                        self.sp_pay_custom.setEnabled(True)
                        self.sp_pay_custom.setValue(float(rate))
                        break

    def _save(self):
        data = {
            "date": qdate_to_date(self.ed_date.date()),
            "start_time": qtime_to_time(self.ed_start.time()),
            "end_time": qtime_to_time(self.ed_end.time()),
            "break_minutes": int(self.ed_break.value()),
            "hours": float(self.ed_hours.value()) if self.ed_hours.value() > 0 else None,
            "entry_type": self.ed_type.currentData(),
            "note": self.ed_note.text().strip() or None,
            "hourly_override": float(self.ed_wage.value()) if self.ed_wage.value() > 0 else None,
            "overtime_hours": float(self.ed_overtime.value()) if self.ed_overtime.value() > 0 else None,
            "location": self.ed_location.text().strip() or None,
        }
        # Pay-Override
        rate = self.cmb_pay.currentData()
        if rate == -2.0:
            data["pay_rate_override"] = float(self.sp_pay_custom.value())
        else:
            data["pay_rate_override"] = float(rate)

        if not data["date"]:
            QMessageBox.warning(self, _t(self.lang, "title_new"), _t(self.lang, "validation_date"))
            return

        try:
            with self.session_factory() as s:
                if self.entry:
                    update_entry(s, self.entry.id, **data)
                else:
                    create_entry(s, self.user_id, **data)
        except Exception as ex:
            QMessageBox.critical(self, _t(self.lang, "title_new"), f"Error: {ex}")
            return

        self.accept()
