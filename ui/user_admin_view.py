# ui/user_admin_view.py  — DROP-IN

from __future__ import annotations

from datetime import datetime as _dt
from typing import List

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QCursor, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QMenu,
    QHeaderView, QStyle
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import User, UserProfile
from core.services.auth_service import hash_password
from languages import tr
from .user_edit_dialog import UserEditDialog


# ---------- Übersetzungs-Helfer ----------
def T(key: str, lang: str, de_fallback: str) -> str:
    """Gibt Übersetzung zurück, oder deutschen Fallback,
    wenn keine Translation existiert (tr(key) == key)."""
    val = tr(key, lang)
    return val if val and val != key else de_fallback


# ---------- Icon-Helfer ----------
def _std_icon(name: str) -> QIcon:
    style = QDialog().style()
    mp = {
        "add": QStyle.StandardPixmap.SP_DialogYesButton,
        "edit": QStyle.StandardPixmap.SP_FileDialogDetailedView,
        "delete": QStyle.StandardPixmap.SP_TrashIcon,
        "refresh": QStyle.StandardPixmap.SP_BrowserReload,
        "key": QStyle.StandardPixmap.SP_DialogResetButton,
    }.get(name, QStyle.StandardPixmap.SP_DesktopIcon)
    return style.standardIcon(mp)


class UserAdminDialog(QDialog):
    # Spaltenindizes
    COL_ID = 0
    COL_USERNAME = 1
    COL_ROLE = 2
    COL_ACTIVE = 3
    COL_LAST_LOGIN = 4
    COL_LOCALE = 5
    COL_FIRST = 6
    COL_LAST = 7
    COL_BDAY = 8
    COL_PHONE = 9
    COL_EMAIL = 10
    COL_EMP_ID = 11
    COL_EMPLOYER = 12
    COL_AHV = 13

    COL_KEYS: List[str] = [
        "id", "username", "role", "active", "last_login", "locale",
        "first_name", "last_name", "birthday", "phone", "email",
        "employee_id", "employer", "ahv_number",
    ]

    def __init__(self, session_factory, lang="de", parent=None, current_user_id=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.lang = lang
        self.current_user_id = current_user_id
        self.setWindowTitle(T("admin.users.title", lang, "Benutzerverwaltung"))
        self._build()
        self._reload()

    # ---------- UI ----------
    def _build(self):
        lay = QVBoxLayout(self)

        # Suche + Buttons
        top = QHBoxLayout()
        self.ed_search = QLineEdit(self)
        self.ed_search.setPlaceholderText(T("admin.users.search", self.lang, "Suche"))
        self.ed_search.textChanged.connect(self._reload)
        top.addWidget(self.ed_search)

        self.btn_refresh = QPushButton(T("common.refresh", self.lang, "Aktualisieren"))
        self.btn_refresh.setIcon(_std_icon("refresh"))
        self.btn_refresh.setStyleSheet("QPushButton{background:#d0e6ff;}")  # himmelblau
        self.btn_refresh.clicked.connect(self._reload)
        top.addWidget(self.btn_refresh)

        self.btn_new = QPushButton(T("common.new", self.lang, "Neu"))
        self.btn_new.setIcon(_std_icon("add"))
        self.btn_new.setStyleSheet("QPushButton{background:#bff0bf;}")  # hellgrün
        self.btn_new.clicked.connect(self._open_new)
        top.addWidget(self.btn_new)

        self.btn_edit = QPushButton(T("common.edit", self.lang, "Bearbeiten"))
        self.btn_edit.setIcon(_std_icon("edit"))
        self.btn_edit.setStyleSheet("QPushButton{background:#e0e0e0;}")  # grau
        self.btn_edit.clicked.connect(self._open_edit)
        top.addWidget(self.btn_edit)

        self.btn_pwd = QPushButton(T("admin.users.reset_pwd", self.lang, "Passwort zurücksetzen"))
        self.btn_pwd.setIcon(_std_icon("key"))
        self.btn_pwd.setStyleSheet("QPushButton{background:#ffe8a6;}")  # gelb
        self.btn_pwd.clicked.connect(self._reset_password_selected)
        top.addWidget(self.btn_pwd)

        self.btn_delete = QPushButton(T("common.delete", self.lang, "Löschen"))
        self.btn_delete.setIcon(_std_icon("delete"))
        self.btn_delete.setStyleSheet("QPushButton{background:#ffb3b3;}")  # hellrot
        self.btn_delete.clicked.connect(self._delete_selected)
        top.addWidget(self.btn_delete)

        lay.addLayout(top)

        # Tabelle
        headers = [
            T("admin.users.col.id", self.lang, "ID"),
            T("admin.users.col.username", self.lang, "Benutzername"),
            T("admin.users.col.role", self.lang, "Rolle"),
            T("admin.users.col.active", self.lang, "Aktiv"),
            T("admin.users.col.last_login", self.lang, "Letzter Login"),
            T("admin.users.col.locale", self.lang, "Sprache"),
            T("admin.users.col.first_name", self.lang, "Vorname"),
            T("admin.users.col.last_name", self.lang, "Nachname"),
            T("admin.users.col.birthday", self.lang, "Geburtstag"),
            T("admin.users.col.phone", self.lang, "Telefon"),
            T("admin.users.col.email", self.lang, "E-Mail"),
            T("admin.users.col.emp_id", self.lang, "Mitarbeiter-ID"),
            T("admin.users.col.employer", self.lang, "Arbeitgeber"),
            T("admin.users.col.ahv", self.lang, "AHV-Nr."),
        ]

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(lambda *_: self._open_edit())

        # WICHTIG: Zeilennummern ausblenden (vermeidet Verwechslung mit ID)
        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(True)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setDefaultSectionSize(130)

        lay.addWidget(self.table)

        # Kontextmenü
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._open_ctx)

        self.resize(1120, 530)

    # ---------- Data ----------
    def _reload(self):
        query = (self.ed_search.text() or "").strip().lower()

        with self.session_factory() as s:  # type: Session
            users = s.execute(select(User).order_by(User.id.asc())).scalars().all()
            profs = {p.user_id: p for p in s.execute(select(UserProfile)).scalars().all()}

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for u in users:
            p = profs.get(u.id)
            row_vals = {
                "id": str(u.id),
                "username": u.username or "",
                "role": (u.role or "").upper(),
                "active": "1" if getattr(u, "is_active", True) else "0",
                "last_login": self._fmt_dt(getattr(u, "last_login", None)),
                "locale": (p.locale if p else "") or "",
                "first_name": (p.first_name if p else "") or "",
                "last_name": (p.last_name if p else "") or "",
                "birthday": p.birthday.isoformat() if (p and p.birthday) else "",
                "phone": (p.phone or "") if p else "",
                "email": (p.email or "") if p else "",
                "employee_id": (p.employee_id or "") if p else "",
                "employer": (p.employer or "") if p else "",
                "ahv_number": (p.ahv_number or "") if p else "",
            }

            if query and not any(query in (v or "").lower() for v in row_vals.values()):
                continue

            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, key in enumerate(self.COL_KEYS):
                text = row_vals.get(key, "")
                it = QTableWidgetItem(text)
                if c == self.COL_ID:
                    it.setData(Qt.ItemDataRole.UserRole, u.id)
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, it)

        self.table.setSortingEnabled(True)
        self.table.sortItems(self.COL_ID, Qt.SortOrder.AscendingOrder)
        self.table.resizeColumnsToContents()

    # ---------- Helpers ----------
    @staticmethod
    def _fmt_dt(v):
        if isinstance(v, _dt):
            return v.strftime("%Y-%m-%d %H:%M")
        return str(v or "")

    def _selected_user_ids(self) -> list[int]:
        ids: list[int] = []
        sel = self.table.selectionModel().selectedRows()
        for idx in sel:
            it = self.table.item(idx.row(), self.COL_ID)
            if not it:
                continue
            uid = it.data(Qt.ItemDataRole.UserRole)
            if uid is None:
                try:
                    uid = int(it.text())
                except Exception:
                    uid = None
            if isinstance(uid, int):
                ids.append(uid)
        return ids

    # ---------- Actions ----------
    def _open_new(self):
        # FIX: UserEditDialog erwartet user_id als Pflichtparameter
        dlg = UserEditDialog(self.session_factory, user_id=None, lang=self.lang, parent=self)
        if dlg.exec():
            self._reload()

    def _open_edit(self):
        ids = self._selected_user_ids()
        if not ids:
            QMessageBox.information(self, "Info", T("admin.users.select_one", self.lang, "Bitte zuerst einen Benutzer auswählen."))
            return
        dlg = UserEditDialog(self.session_factory, user_id=ids[0], lang=self.lang, parent=self)
        if dlg.exec():
            self._reload()

    def _reset_password_selected(self):
        ids = self._selected_user_ids()
        if not ids:
            QMessageBox.information(self, "Info", T("admin.users.select_one", self.lang, "Bitte zuerst einen Benutzer auswählen."))
            return
        uid = ids[0]
        default_pwd = T("admin.users.reset_pwd_default", self.lang, "ChangeMe123")

        ok = QMessageBox.question(
            self,
            T("admin.users.reset_pwd", self.lang, "Passwort zurücksetzen"),
            f'{T("admin.users.reset_pwd_confirm", self.lang, "Passwort wirklich zurücksetzen?")}\n\n'
            f'User-ID: {uid}\nNeues Passwort: {default_pwd}',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        with self.session_factory() as s:
            u = s.get(User, uid)
            if not u:
                QMessageBox.warning(self, "Fehler", "Benutzer nicht gefunden.")
                return
            u.password_hash = hash_password(default_pwd)
            s.add(u)
            s.commit()

        QMessageBox.information(self, "OK", T("admin.users.reset_pwd_done", self.lang, "Passwort zurückgesetzt."))
        self._reload()

    def _delete_selected(self):
        ids = self._selected_user_ids()
        if not ids:
            QMessageBox.information(self, "Info", T("admin.users.select_any", self.lang, "Bitte Benutzer auswählen."))
            return
        if self.current_user_id in ids:
            QMessageBox.warning(self, "Achtung", T("admin.users.cant_delete_self", self.lang, "Der aktuell angemeldete Benutzer kann nicht gelöscht werden."))
            return

        ok = QMessageBox.question(
            self,
            T("common.delete", self.lang, "Löschen"),
            T("admin.users.delete_confirm", self.lang, "Sollen die ausgewählten Benutzer gelöscht werden?") + f" ({len(ids)}x)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        with self.session_factory() as s:
            for uid in ids:
                u = s.get(User, uid)
                if u:
                    s.delete(u)
            s.commit()
        self._reload()

    # ---------- Kontextmenü ----------
    def _open_ctx(self, pos: QPoint):
        menu = QMenu(self)

        act_new = QAction(_std_icon("add"), T("common.new", self.lang, "Neu"), self)
        act_new.triggered.connect(self._open_new)
        menu.addAction(act_new)

        act_edit = QAction(_std_icon("edit"), T("common.edit", self.lang, "Bearbeiten"), self)
        act_edit.triggered.connect(self._open_edit)
        menu.addAction(act_edit)

        act_pwd = QAction(_std_icon("key"), T("admin.users.reset_pwd", self.lang, "Passwort zurücksetzen"), self)
        act_pwd.triggered.connect(self._reset_password_selected)
        menu.addAction(act_pwd)

        act_del = QAction(_std_icon("delete"), T("common.delete", self.lang, "Löschen"), self)
        act_del.triggered.connect(self._delete_selected)
        menu.addAction(act_del)

        menu.addSeparator()

        act_ref = QAction(_std_icon("refresh"), T("common.refresh", self.lang, "Aktualisieren"), self)
        act_ref.triggered.connect(self._reload)
        menu.addAction(act_ref)

        menu.exec(QCursor.pos())
