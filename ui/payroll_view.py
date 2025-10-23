from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QSpinBox, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox, QFileDialog, QFrame
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from languages import tr
from core.services.payroll_service import (
    recalc_and_save, export_pdf, export_xlsx_range, lock_run, unlock_run
)
from core.models import User, PayrollRun, UserProfile
from core.utils.users import user_label
from core.services.log_service import log_activity, log_error
from datetime import date, timedelta
import calendar
from ui.window_flags import apply_window_controls
import json

from datetime import date as _date, datetime as _dt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QInputDialog
from PySide6.QtCore import Qt
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from core.utils.i18n import t
from core.utils.formatting import fmt_date, fmt_datetime
from core.models import User, UserProfile
from .user_edit_dialog import UserEditDialog

# Fallback-Übersetzungen, falls languages.py (calendar.entry_types.*) fehlt
_TYPES_FALLBACK = {
    "de": {"work":"Arbeit","vacation":"Urlaub","sick":"Krank","holiday":"Feiertag","off":"Frei","other":"Sonstiges",
           "appointment":"Arzttermin","hospital":"Spital"},
    "en": {"work":"Work","vacation":"Vacation","sick":"Sick","holiday":"Holiday","off":"Off","other":"Other",
           "appointment":"Appointment","hospital":"Hospital"},
    "sr": {"work":"Rad","vacation":"Odmor","sick":"Bolovanje","holiday":"Praznik","off":"Slobodno","other":"Ostalo",
           "appointment":"Pregled","hospital":"Bolnica"},
}
def _type_label(lang: str, code: str) -> str:
    if not code:
        return ""
    if code.startswith("CUSTOM:"):
        return code.split(":", 1)[1] or "Custom"
    key = (code or "").lower()
    from languages import tr as _tr
    txt = _tr(f"calendar.entry_types.{key}", lang)
    if txt == f"calendar.entry_types.{key}":
        return _TYPES_FALLBACK.get(lang, _TYPES_FALLBACK["de"]).get(key, code)
    return txt

class PayrollDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, user_id: int, lang: str = "de", is_admin: bool = False, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user_id = user_id
        self.lang = lang
        self.is_admin = is_admin
        self.setWindowTitle(tr("payroll.title", self.lang) if tr("payroll.title", self.lang) != "payroll.title" else "Monatsabschluss – Abrechnung")
        self.setSizeGripEnabled(True)
        self._build()
        self.adjustSize()

    # ----------------------- Hilfsfunktionen -----------------------
    def _target_user(self) -> int:
        return self.user_combo.currentData() if self.user_combo is not None else self.current_user_id

    def _ym_from(self) -> tuple[int,int]:
        return int(self.spin_year.value()), int(self.spin_month.value())

    def _ym_to(self) -> tuple[int,int]:
        return int(self.spin_year_to.value()), int(self.spin_month_to.value())

    def _period_label(self) -> str:
        y1, m1 = self._ym_from(); y2, m2 = self._ym_to()
        if (y1, m1) == (y2, m2):
            return f"{y1}-{m1:02d}"
        return f"{y1}-{m1:02d} bis {y2}-{m2:02d}"

    def _period_dates(self) -> tuple[date,date]:
        """Erster Tag Startmonat, letzter Tag Endmonat."""
        y1, m1 = self._ym_from(); y2, m2 = self._ym_to()
        start = date(y1, m1, 1)
        last_day = calendar.monthrange(y2, m2)[1]
        end = date(y2, m2, last_day)
        return start, end

    def _export_filename(self, uid: int, ext: str) -> str:
        """Abrechnung_Nachname-Vorname_erstellt-am-YYYY-MM-DD_von_YYYY-MM-DD_bis_YYYY-MM-DD.ext"""
        with self.session_factory() as s:
            u = s.get(User, uid)
            p = s.execute(select(UserProfile).where(UserProfile.user_id==uid)).scalar_one_or_none()
        ln = (p.last_name or "").strip() if p else ""
        fn = (p.first_name or "").strip() if p else (u.username if u else "User")
        start, end = self._period_dates()
        created = date.today().strftime("%Y-%m-%d")
        safe_name = f"{ln}-{fn}".strip().replace(" ", "-")
        return f"Abrechnung_{safe_name}_erstellt-am-{created}_von_{start.isoformat()}_bis_{end.isoformat()}.{ext}"

    def _month_locked(self, uid: int, y: int, m: int) -> bool:
        with self.session_factory() as s:
            run = s.execute(select(PayrollRun).where(PayrollRun.user_id==uid, PayrollRun.period_year==y, PayrollRun.period_month==m)).scalar_one_or_none()
            return bool(run and run.is_locked)

    def _update_status_frame(self):
        uid = self._target_user()
        y1, m1 = self._ym_from()
        locked = self._month_locked(uid, y1, m1)
        color = "#222"  # offen = schwarz
        text = "Status: Offen"
        if locked:
            color = "#1e8e3e"  # grün
            text = "Status: Abgeschlossen"
        if getattr(self, "_status_last_action", None) == "reopen":
            color = "#d93025"  # rot
            text = "Status: Re-Open (offen)"
        self.status_label.setText(text)
        self.status_frame.setStyleSheet(f"QFrame#statusFrame {{ border: 3px solid {color}; border-radius: 6px; padding:4px; }}")

    # ----------------------- UI -----------------------
    def _build(self):
        layout = QVBoxLayout(self)
        apply_window_controls(self)
        # Top-Zeile: User + Zeitraum + Recalc
        top = QHBoxLayout()
        if self.is_admin:
            self.user_combo = QComboBox()
            with self.session_factory() as s:
                users = s.execute(select(User).order_by(User.username.asc())).scalars().all()
                profs = {p.user_id: p for p in s.execute(select(UserProfile)).scalars().all()}
            for u in users:
                p = profs.get(u.id)
                last = (p.last_name or "") if p else ""
                first = (p.first_name or "") if p else ""
                employer = (p.employer or "—") if p else "—"
                role = (u.role or "").upper()
                label = f"{last} {first} - {employer} ({role})".strip()
                self.user_combo.addItem(label, u.id)

            idx = self.user_combo.findData(self.current_user_id)  # <— NEU
            if idx >= 0:
                self.user_combo.setCurrentIndex(idx)

            self.user_combo.currentIndexChanged.connect(self._recalc)
            top.addWidget(self.user_combo)
        else:
            self.user_combo = None

        self.spin_year = QSpinBox();  self.spin_year.setRange(2000, 2100); self.spin_year.setValue(date.today().year)
        self.spin_month = QSpinBox(); self.spin_month.setRange(1, 12);     self.spin_month.setValue(date.today().month)
        self.spin_year_to = QSpinBox();  self.spin_year_to.setRange(2000, 2100); self.spin_year_to.setValue(date.today().year)
        self.spin_month_to = QSpinBox(); self.spin_month_to.setRange(1, 12);     self.spin_month_to.setValue(date.today().month)
        btn_recalc = QPushButton(tr("payroll.recalc", self.lang) if tr("payroll.recalc", self.lang) != "payroll.recalc" else "Berechnen / Aktualisieren")

        for w in filter(None, [self.spin_year, self.spin_month, self.spin_year_to, self.spin_month_to, btn_recalc]):
            top.addWidget(w)
        layout.addLayout(top)

        # Status-Rahmen (zeigt Abgeschlossen/Offen/soeben Re-Open)
        self.status_frame = QFrame(objectName="statusFrame")
        self.status_label = QLabel("Status: —")
        sbox = QHBoxLayout(self.status_frame); sbox.addWidget(self.status_label); sbox.addStretch(1)
        layout.addWidget(self.status_frame)

        # KPIs
        self.lbl_hours  = QLabel((tr("payroll.hours_total", self.lang) if tr("payroll.hours_total", self.lang) != "payroll.hours_total" else "Stunden Total") + ": —")
        self.lbl_entries= QLabel((tr("payroll.entries", self.lang)     if tr("payroll.entries", self.lang)     != "payroll.entries"     else "Einträge") + ": —")
        self.lbl_gross  = QLabel((tr("payroll.gross", self.lang)       if tr("payroll.gross", self.lang)       != "payroll.gross"       else "Bruttolohn") + ": —")
        self.lbl_net    = QLabel((tr("payroll.net", self.lang)         if tr("payroll.net", self.lang)         != "payroll.net"         else "Nettolohn") + ": —")
        layout.addWidget(self.lbl_hours); layout.addWidget(self.lbl_entries); layout.addWidget(self.lbl_gross); layout.addWidget(self.lbl_net)

        # Breakdown
        self.tbl_bd = QTableWidget(0, 3)
        self.tbl_bd.setHorizontalHeaderLabels([
            tr("calendar.type", self.lang) if tr("calendar.type", self.lang) != "calendar.type" else "Typ",
            tr("calendar.hours", self.lang) if tr("calendar.hours", self.lang) != "calendar.hours" else "Stunden",
            tr("payroll.entries", self.lang) if tr("payroll.entries", self.lang) != "payroll.entries" else "Einträge"
        ])
        layout.addWidget(self.tbl_bd)

        # Aktionen
        actions = QHBoxLayout()
        self.btn_pdf   = QPushButton(tr("payroll.pdf", self.lang)  if tr("payroll.pdf", self.lang)  != "payroll.pdf"  else "PDF Lohnschein")
        self.btn_xlsx  = QPushButton(tr("payroll.xlsx", self.lang) if tr("payroll.xlsx", self.lang) != "payroll.xlsx" else "Excel Lohnschein")
        self.btn_lock  = QPushButton(tr("payroll.lock", self.lang) if tr("payroll.lock", self.lang) != "payroll.lock" else "Abschließen")
        self.btn_unlock= QPushButton(tr("payroll.unlock", self.lang) if tr("payroll.unlock", self.lang) != "payroll.unlock" else "Re-Open")
        self.edit_reason = QLineEdit(); self.edit_reason.setPlaceholderText(tr("payroll.reason_prompt", self.lang) if tr("payroll.reason_prompt", self.lang) != "payroll.reason_prompt" else "Begründung für Re-Open (optional)")
        for w in (self.btn_pdf, self.btn_xlsx, self.btn_lock, self.btn_unlock, self.edit_reason):
            actions.addWidget(w)
        layout.addLayout(actions)

        # Nur Admin darf Lock/Unlock
        self.btn_lock.setEnabled(self.is_admin)
        self.btn_unlock.setEnabled(self.is_admin)

        # Signals
        btn_recalc.clicked.connect(self._recalc)
        self.btn_pdf.clicked.connect(self._export_pdf)
        self.btn_xlsx.clicked.connect(self._export_xlsx)
        self.btn_lock.clicked.connect(self._lock)
        self.btn_unlock.clicked.connect(self._unlock)

        # Initial
        self._recalc()
        self._update_status_frame()
        self.adjustSize()

    # ----------------------- Recalc -----------------------
    def _recalc(self):
        uid = self._target_user()
        y1, m1 = self._ym_from(); y2, m2 = self._ym_to()

        hours_total = 0.0; entries_total = 0; gross_total = 0.0; net_total = 0.0
        breakdown = {}

        y, m = y1, m1
        with self.session_factory() as s:
            while (y < y2) or (y == y2 and m <= m2):
                run = recalc_and_save(s, uid, y, m)
                hours_total   += float(run.hours_total or 0.0)
                entries_total += int(run.entries_count or 0)
                gross_total   += float(run.gross_total or 0.0)
                net_total     += float(run.net_total or 0.0)
                bd = json.loads(run.type_breakdown_json or "{}")
                for typ, vals in bd.items():
                    b = breakdown.setdefault(typ, {"hours":0.0,"count":0})
                    b["hours"] += float(vals.get("hours",0.0)); b["count"] += int(vals.get("count",0))
                if m == 12: y, m = y+1, 1
                else: m += 1

        self.lbl_hours.setText(f"{tr('payroll.hours_total', self.lang) if tr('payroll.hours_total', self.lang) != 'payroll.hours_total' else 'Stunden Total'}: {hours_total:.2f}")
        self.lbl_entries.setText(f"{tr('payroll.entries', self.lang) if tr('payroll.entries', self.lang) != 'payroll.entries' else 'Einträge'}: {entries_total}")
        self.lbl_gross.setText(f"{tr('payroll.gross', self.lang) if tr('payroll.gross', self.lang) != 'payroll.gross' else 'Bruttolohn'}: CHF {gross_total:.2f}")
        self.lbl_net.setText(f"{tr('payroll.net', self.lang) if tr('payroll.net', self.lang) != 'payroll.net' else 'Nettolohn'}: CHF {net_total:.2f}")

        self.tbl_bd.setRowCount(0)
        for typ, vals in breakdown.items():
            r=self.tbl_bd.rowCount(); self.tbl_bd.insertRow(r)
            self.tbl_bd.setItem(r,0,QTableWidgetItem(_type_label(self.lang, typ)))
            self.tbl_bd.setItem(r,1,QTableWidgetItem(f"{float(vals.get('hours',0.0)):.2f}"))
            self.tbl_bd.setItem(r,2,QTableWidgetItem(str(int(vals.get('count',0)))))

        # Status aktualisieren
        self._status_last_action = None
        self._update_status_frame()
        self.adjustSize()

    # ----------------------- Export -----------------------
    def _export_pdf(self):
        uid = self._target_user()
        y1, m1 = self._ym_from(); y2, m2 = self._ym_to()
        fname = self._export_filename(uid, "pdf")
        path, _ = QFileDialog.getSaveFileName(self, "PDF speichern", fname, "PDF (*.pdf)")
        if not path: return
        try:
            with self.session_factory() as s:
                export_pdf(s, uid, y1, m1, y2, m2, path, lang=self.lang)
            QMessageBox.information(self, "PDF", f"Exportiert: {path}")
            log_activity(self.current_user_id, "payroll.export_pdf", {"user_id": uid, "file": path})
        except Exception as ex:
            QMessageBox.critical(self, "PDF", str(ex))
            log_error("Fehler beim Export PDF", exc=ex)

    def _export_xlsx(self):
        uid = self._target_user()
        y1, m1 = self._ym_from(); y2, m2 = self._ym_to()
        fname = self._export_filename(uid, "xlsx")
        path, _ = QFileDialog.getSaveFileName(self, "Excel speichern", fname, "Excel (*.xlsx)")
        if not path: return
        try:
            with self.session_factory() as s:
                export_xlsx_range(s, uid, y1, m1, y2, m2, path, lang=self.lang)
            QMessageBox.information(self, "Excel", f"Exportiert: {path}")
            log_activity(self.current_user_id, "payroll.export_xlsx", {"user_id": uid, "file": path})
        except Exception as ex:
            QMessageBox.critical(self, "Excel", str(ex))
            log_error("Fehler beim Export EXCEL", exc=ex)

    # ----------------------- Lock / Unlock -----------------------
    def _lock(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Abrechnung", "Nur ADMIN darf abschließen.")
            return
        uid = self._target_user()
        y1, m1 = self._ym_from()
        y2, m2 = self._ym_to()
        with self.session_factory() as s:
            lock_run(s, uid, y1, m1, by_user_id=self.current_user_id)
        start, end = self._period_dates()
        QMessageBox.information(self, "Abrechnung", f"Sie haben von {start.isoformat()} bis {end.isoformat()} erfolgreich abgeschlossen.\n(Hinweis: technisch wird nur der Startmonat abgeschlossen.)")
        self._status_last_action = "lock"
        self._update_status_frame()
        log_activity(self.current_user_id, "payroll.lock", {"user_id": uid, "from": start.isoformat(), "to": end.isoformat(), "locked_month": f"{y1}-{m1:02d}"})
        self._recalc()

    def _unlock(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Abrechnung", "Nur ADMIN darf Re-Open ausführen.")
            return
        uid = self._target_user()
        y1, m1 = self._ym_from()
        y2, m2 = self._ym_to()
        reason = self.edit_reason.text().strip()
        with self.session_factory() as s:
            unlock_run(s, uid, y1, m1, reason or "")
        start, end = self._period_dates()
        QMessageBox.information(self, "Abrechnung", f"Sie haben von {start.isoformat()} bis {end.isoformat()} erfolgreich wieder geöffnet.\n(Hinweis: technisch wird nur der Startmonat geöffnet.)")
        self._status_last_action = "reopen"
        self._update_status_frame()
        log_activity(self.current_user_id, "payroll.unlock", {"user_id": uid, "from": start.isoformat(), "to": end.isoformat(), "unlocked_month": f"{y1}-{m1:02d}", "reason": reason})
        self._recalc()
