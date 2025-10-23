from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout
from sqlalchemy.orm import sessionmaker
from core.services.notification_service import list_unread, mark_all_read
from core.utils.formatting import fmt_datetime
from PySide6.QtCore import Qt
from typing import Any
from pathlib import Path
from languages import tr as _tr
import os  # <- wichtig, damit os.path/... funktioniert

_LOG_MISSING = True
_MISSING_SEEN: set[str] = set()
_LOG_DIR = Path(os.path.dirname(os.path.dirname(__file__))).parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_MISSING_FILE = _LOG_DIR / "i18n_missing.log"

def t(key: str, lang: str, **kwargs: Any) -> str:
    """
    i18n-Helper mit format(**kwargs).
    - Wenn Key fehlt, wird 'key' zurückgegeben.
    - Fehlende Keys werden (einmalig) ins Log geschrieben (dev).
    """
    txt = _tr(key, lang)
    if txt == key:
        if _LOG_MISSING and key not in _MISSING_SEEN:
            try:
                with open(_MISSING_FILE, "a", encoding="utf-8") as f:
                    f.write(key + "\n")
            except Exception:
                pass
            _MISSING_SEEN.add(key)
    try:
        return txt.format(**kwargs)
    except Exception:
        return txt

class NotificationCenter(QDialog):
    def __init__(self, session_factory: sessionmaker, user_id: int, lang: str="de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory; self.user_id = user_id; self.lang = lang
        self.setWindowTitle(t("notif.title", self.lang) if t("notif.title", self.lang)!="notif.title" else "Benachrichtigungen")
        self.setSizeGripEnabled(True)
        self._build(); self.adjustSize()

    def _build(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([t("calendar.date", self.lang) if t("calendar.date", self.lang)!="calendar.date" else "Zeit",
                                              t("notif.col.title", self.lang) if t("notif.col.title", self.lang)!="notif.col.title" else "Titel",
                                              t("notif.col.body", self.lang) if t("notif.col.body", self.lang)!="notif.col.body" else "Nachricht"])
        layout.addWidget(self.table)
        row = QHBoxLayout()
        btn_ok = QPushButton(t("dialogs.common.ok", self.lang) if t("dialogs.common.ok", self.lang)!="dialogs.common.ok" else "OK")
        btn_mark = QPushButton(t("notif.mark_all", self.lang) if t("notif.mark_all", self.lang)!="notif.mark_all" else "Alle als gelesen")
        row.addWidget(btn_mark); row.addWidget(btn_ok); layout.addLayout(row)
        btn_ok.clicked.connect(self.accept); btn_mark.clicked.connect(self._mark_read); self._reload()

    def _reload(self):
        with self.session_factory() as s: rows = list_unread(s, self.user_id)
        self.table.setRowCount(0)
        for n in rows:
            i=self.table.rowCount(); self.table.insertRow(i)
            it_time = QTableWidgetItem(fmt_datetime(n.created_at, self.lang)); it_time.setData(Qt.EditRole, str(n.created_at))
            self.table.setItem(i,0, it_time)
            self.table.setItem(i,1, QTableWidgetItem(n.title))
            self.table.setItem(i,2, QTableWidgetItem(n.body))
        self.table.resizeColumnsToContents(); self.adjustSize()

    def _mark_read(self):
        with self.session_factory() as s: mark_all_read(s, self.user_id)
        self._reload()
