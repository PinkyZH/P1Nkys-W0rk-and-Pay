from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QComboBox, \
    QLabel
from sqlalchemy import select, desc
from sqlalchemy.orm import sessionmaker

from core.models import AuditLog, User
from core.utils.formatting import fmt_datetime
from core.utils.i18n import t
from ui.window_flags import apply_window_controls


class AuditLogDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.lang = lang
        self.setWindowTitle(
            t("tools.audit_log", self.lang) if t("tools.audit_log", self.lang) != "tools.audit_log" else "Audit-Log")
        self.setMinimumWidth(1000)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        filter_row = QHBoxLayout()
        self.combo_user = QComboBox();
        self.combo_user.addItem(
            t("admin_users.name", self.lang) + ": " + t("calendar.all", self.lang) if t("calendar.all",
                                                                                        self.lang) != "calendar.all" else "Alle",
            None)
        with self.session_factory() as s:
            users = s.execute(select(User).order_by(User.username.asc())).scalars().all()
        for u in users:
            self.combo_user.addItem(u.username, u.id)
        btn_reload = QPushButton(t("admin_users.refresh", self.lang))
        filter_row.addWidget(QLabel(t("admin_users.username", self.lang)));
        filter_row.addWidget(self.combo_user);
        filter_row.addWidget(btn_reload)
        layout.addLayout(filter_row)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [t("calendar.date", self.lang), "User", "Aktion", "Entity", "Entity-ID", "Before", "After"])
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        btn_reload.clicked.connect(self._load)
        self._load()
        apply_window_controls(self)

    def _load(self):
        uid = self.combo_user.currentData()
        with self.session_factory() as s:
            stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(1000)
            if uid:
                stmt = stmt.where(AuditLog.user_id == uid)
            rows = s.execute(stmt).scalars().all()
            users = {u.id: u.username for u in s.execute(select(User)).scalars().all()}
        was = self.table.isSortingEnabled()
        if was: self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for a in rows:
            i = self.table.rowCount();
            self.table.insertRow(i)
            it_time = QTableWidgetItem(fmt_datetime(a.created_at, self.lang));
            it_time.setData(Qt.EditRole, str(a.created_at))
            self.table.setItem(i, 0, it_time)
            self.table.setItem(i, 1, QTableWidgetItem(users.get(a.user_id, "-") if a.user_id else "-"))
            self.table.setItem(i, 2, QTableWidgetItem(a.action))
            self.table.setItem(i, 3, QTableWidgetItem(a.entity))
            self.table.setItem(i, 4, QTableWidgetItem(a.entity_id or ""))
            self.table.setItem(i, 5, QTableWidgetItem(a.before_json or ""))
            self.table.setItem(i, 6, QTableWidgetItem(a.after_json or ""))
        if was: self.table.setSortingEnabled(True)
