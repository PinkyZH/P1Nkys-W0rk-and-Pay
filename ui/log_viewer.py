from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QHBoxLayout, QComboBox, QPushButton, QTextEdit, QLabel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from core.models import User
from core.services.log_service import list_user_log_files, read_log, ERROR_FILE
from ui.window_flags import apply_window_controls
from core.utils.i18n import t

class LogViewerDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, lang: str="de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory; self.lang = lang
        self.setWindowTitle(t("tools.log_viewer", self.lang) if t("tools.log_viewer", self.lang)!="tools.log_viewer" else "Log-Viewer")
        apply_window_controls(self, size_grip=True)
        self._build(); self.adjustSize()

    def _build(self):
        root = QVBoxLayout(self); tabs = QTabWidget(); root.addWidget(tabs)

        w1 = QWidget(); tabs.addTab(w1, t("tools.user_logs", self.lang) if t("tools.user_logs", self.lang)!="tools.user_logs" else "Benutzer-Logs")
        l1 = QVBoxLayout(w1)
        row = QHBoxLayout()
        self.combo_user = QComboBox(); self.combo_user.addItem((t("admin_users.username", self.lang) if t("admin_users.username", self.lang)!="admin_users.username" else "Benutzername")+": -", None)
        with self.session_factory() as s:
            users = s.execute(select(User).order_by(User.username.asc())).scalars().all()
        for u in users: self.combo_user.addItem(u.username, u.id)
        btn_load_user = QPushButton(t("dialogs.common.load", self.lang) if t("dialogs.common.load", self.lang)!="dialogs.common.load" else "Laden")
        row.addWidget(QLabel(t("admin_users.username", self.lang))); row.addWidget(self.combo_user, 1); row.addWidget(btn_load_user); l1.addLayout(row)
        self.txt_user = QTextEdit(); self.txt_user.setReadOnly(True); l1.addWidget(self.txt_user, 1)

        w2 = QWidget(); tabs.addTab(w2, t("tools.error_log", self.lang) if t("tools.error_log", self.lang)!="tools.error_log" else "Fehler-Log")
        l2 = QVBoxLayout(w2); btn_load_err = QPushButton(t("dialogs.common.refresh", self.lang) if t("dialogs.common.refresh", self.lang)!="dialogs.common.refresh" else "Aktualisieren")
        l2.addWidget(btn_load_err); self.txt_err = QTextEdit(); self.txt_err.setReadOnly(True); l2.addWidget(self.txt_err, 1)

        btn_load_user.clicked.connect(self._load_user_log); btn_load_err.clicked.connect(self._load_err_log)

    def _load_user_log(self):
        uid = self.combo_user.currentData()
        from core.services.log_service import USER_DIR
        p = USER_DIR / f"{uid}.log"
        self.txt_user.setPlainText(read_log(p))

    def _load_err_log(self):
        self.txt_err.setPlainText(read_log(Path(ERROR_FILE)))
