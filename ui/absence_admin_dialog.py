from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from core.services.absence_service import list_requests, decide_absence
from core.services.log_service import log_activity, log_error
from core.models import User, UserProfile
from languages import tr
from ui.window_flags import apply_window_controls

def _type_label(lang: str, code: str) -> str:
    """Übersetzt den Abwesenheitstyp über calendar.entry_types.*, inkl. CUSTOM:..."""
    if not code:
        return ""
    if code.startswith("CUSTOM:"):
        # Benutzerdefinierte Bezeichnung nach Doppelpunkt
        return code.split(":", 1)[1] or "Custom"
    key = (code or "").lower()
    lbl = tr(f"calendar.entry_types.{key}", lang)
    if lbl == f"calendar.entry_types.{key}":
        # Fallback deutsch/englisch/serbisch minimal
        fallback = {
            "work": {"de": "Arbeit", "en": "Work", "sr": "Rad"},
            "vacation": {"de": "Urlaub", "en": "Vacation", "sr": "Odmor"},
            "sick": {"de": "Krank", "en": "Sick", "sr": "Bolovanje"},
            "holiday": {"de": "Feiertag", "en": "Holiday", "sr": "Praznik"},
            "off": {"de": "Frei", "en": "Off", "sr": "Slobodno"},
            "other": {"de": "Sonstiges", "en": "Other", "sr": "Ostalo"},
            "appointment": {"de": "Arzttermin", "en": "Appointment", "sr": "Pregled"},
            "hospital": {"de": "Spital", "en": "Hospital", "sr": "Bolnica"},
        }
        return fallback.get(key, {}).get(lang, code)
    return lbl


def _status_label(lang: str, status: str) -> str:
    """Übersetzt PENDING/APPROVED/DENIED via abs.status.* mit Fallback."""
    key = (status or "").lower()
    lbl = tr(f"abs.status.{key}", lang)
    if lbl != f"abs.status.{key}":
        return lbl
    fb = {
        "pending": {"de": "Ausstehend", "en": "Pending", "sr": "Na čekanju"},
        "approved": {"de": "Bewilligt", "en": "Approved", "sr": "Odobren"},
        "denied": {"de": "Abgelehnt", "en": "Rejected", "sr": "Odbijen"},
    }
    return fb.get(key, {}).get(lang, status or "")


class AbsenceAdminDialog(QDialog):
    """
    Abwesenheiten – Verwaltung (Admin/HR):
      - sortierbare Tabelle
      - Genehmigen / Ablehnen (+ Notifikation)
      - Mehrsprachige Spaltentitel, Typ & Status
      - Spalten: ID | Benutzername | Name | Typ | Von | Bis | Status | Grund | Custom
    """

    def __init__(self, session_factory: sessionmaker, current_user_id: int,
                 is_admin_or_hr: bool, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.current_user_id = current_user_id
        self.is_admin_or_hr = is_admin_or_hr
        self.lang = lang

        title = tr("hr.absence_admin", self.lang)
        self.setWindowTitle(title if title != "hr.absence_admin" else "Abwesenheiten – Verwaltung")
        self.setMinimumWidth(1100)
        self._build()

    # ---------------- UI ----------------
    def _build(self):
        layout = QVBoxLayout(self)

        # Mehrsprachige Spaltentitel (mit Fallback)
        headers = [
            "ID",
            tr("admin_users.username", self.lang) if tr("admin_users.username", self.lang) != "admin_users.username" else "Benutzername",
            tr("admin_users.name", self.lang)     if tr("admin_users.name", self.lang)     != "admin_users.name"     else "Name",
            tr("calendar.type", self.lang)        if tr("calendar.type", self.lang)        != "calendar.type"        else "Typ",
            tr("from", self.lang)                 if tr("from", self.lang)                 != "from"                 else "Von",
            tr("to", self.lang)                   if tr("to", self.lang)                   != "to"                   else "Bis",
            tr("status", self.lang)               if tr("status", self.lang)               != "status"               else "Status",
            tr("reason", self.lang)               if tr("reason", self.lang)               != "reason"               else "Grund",
            tr("abs.custom_label", self.lang)     if tr("abs.custom_label", self.lang)     != "abs.custom_label"     else "Custom-Label",
        ]
        self.COL_ID, self.COL_USER, self.COL_NAME, self.COL_TYPE, self.COL_FROM, self.COL_TO, self.COL_STATUS, self.COL_REASON, self.COL_CUSTOM = range(len(headers))

        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        row = QHBoxLayout()
        btn_reload  = QPushButton(tr("admin_users.refresh", self.lang) if tr("admin_users.refresh", self.lang) != "admin_users.refresh" else "Aktualisieren")
        btn_approve = QPushButton(tr("approve", self.lang) if tr("approve", self.lang) != "approve" else "Genehmigen")
        btn_deny    = QPushButton(tr("deny", self.lang) if tr("deny", self.lang) != "deny" else "Ablehnen")
        row.addWidget(btn_reload); row.addWidget(btn_approve); row.addWidget(btn_deny)
        layout.addLayout(row)

        btn_reload.clicked.connect(self._load)
        btn_approve.clicked.connect(lambda: self._decide(True))
        btn_deny.clicked.connect(lambda: self._decide(False))

        apply_window_controls(self)
        self._load()

    # ---------------- Data ----------------
    def _load(self):
        hdr = self.table.horizontalHeader()
        sort_col, sort_order = hdr.sortIndicatorSection(), hdr.sortIndicatorOrder()
        sorting_on = self.table.isSortingEnabled()
        if sorting_on: self.table.setSortingEnabled(False)

        # Nutzer + Profil für Namen
        with self.session_factory() as s:
            rows = list_requests(s, None)
            users = {u.id: u for u in s.execute(select(User)).scalars().all()}
            profs = {p.user_id: p for p in s.execute(select(UserProfile)).scalars().all()}

        self.table.setRowCount(0)
        for a in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)

            def set_item(col: int, text: str, sort_val=None):
                it = QTableWidgetItem(text if text is not None else "")
                if sort_val is not None:
                    it.setData(Qt.EditRole, sort_val)
                self.table.setItem(i, col, it)

            u = users.get(a.user_id)
            p = profs.get(a.user_id)

            username = u.username if u else str(a.user_id)
            fullname = f"{(p.last_name or '')} {(p.first_name or '')}".strip() if p else ""
            set_item(self.COL_ID, str(a.id), int(a.id))
            set_item(self.COL_USER, username)
            set_item(self.COL_NAME, fullname)
            set_item(self.COL_TYPE, _type_label(self.lang, a.type or ""))

            if a.date_from:
                set_item(self.COL_FROM, a.date_from.isoformat(), int(a.date_from.strftime("%Y%m%d")))
            else:
                set_item(self.COL_FROM, "", 0)
            if a.date_to:
                set_item(self.COL_TO, a.date_to.isoformat(), int(a.date_to.strftime("%Y%m%d")))
            else:
                set_item(self.COL_TO, "", 0)

            set_item(self.COL_STATUS, _status_label(self.lang, a.status or ""))
            set_item(self.COL_REASON, a.reason or "")
            set_item(self.COL_CUSTOM, a.custom_label or "")

        self.table.resizeColumnsToContents()

        if sorting_on:
            self.table.setSortingEnabled(True)
            try:
                self.table.sortItems(sort_col, sort_order)
            except Exception:
                pass

    # ------------- Actions ---------------
    def _current_request_id(self) -> Optional[int]:
        r = self.table.currentRow()
        if r < 0:
            return None
        it = self.table.item(r, self.COL_ID)
        return int(it.text()) if it else None

    def _decide(self, approve: bool):
        if not self.is_admin_or_hr:
            QMessageBox.warning(self, "Rechte", "Nur ADMIN/HR dürfen entscheiden.")
            return

        req_id = self._current_request_id()
        if req_id is None:
            return

        with self.session_factory() as s:
            try:
                a = decide_absence(s, req_id, approve, decided_by=self.current_user_id)
                status_txt = _status_label(self.lang, "APPROVED" if approve else "DENIED")
                QMessageBox.information(self, "Entscheid", f"Antrag {status_txt}.")

                # 🔔 Benachrichtigung
                from core.services.notification_service import create_notification
                title_map = {"de": "Abwesenheit", "en": "Absence", "sr": "Odsustvo"}
                msg_map = {
                    "de": f"Ihr Abwesenheitsantrag ({_type_label(self.lang, a.type)}) von {a.date_from} bis {a.date_to} wurde {'bewilligt' if approve else 'abgelehnt'}.",
                    "en": f"Your absence request ({_type_label(self.lang, a.type)}) from {a.date_from} to {a.date_to} was {'approved' if approve else 'rejected'}.",
                    "sr": f"Vaš zahtev za odsustvo ({_type_label(self.lang, a.type)}) od {a.date_from} do {a.date_to} je {'odobren' if approve else 'odbijen'}."
                }
                t = title_map.get(self.lang, "Absence")
                m = msg_map.get(self.lang, msg_map["de"])
                create_notification(s, a.user_id, t, m)

                log_activity(self.current_user_id, "absence.decide", {"request_id": req_id, "approve": approve})
            except Exception as ex:
                QMessageBox.critical(self, "Fehler", str(ex))
                log_error("Fehler bei Absenzen", exc=ex)
                return

        self._load()
