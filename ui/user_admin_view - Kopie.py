from __future__ import annotations

from datetime import date as _date, datetime as _dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QMenu, QHeaderView
)
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from core.models import User, UserProfile
from core.services.user_service import delete_user
from languages import tr
from ui.window_flags import apply_window_controls
from .registration_dialog import RegistrationDialog
from .user_edit_dialog import UserEditDialog


# optional Icon-Helper – falls bereits vorhanden, wird dieser hier ignoriert
def _icon(name: str):
    try:
        from ui.icons import icon
        return icon(name)
    except Exception:
        from PySide6.QtGui import QIcon
        return QIcon()


COLS = [
    "id", "username", "role", "active", "last_login", "locale",
    "first_name", "last_name", "birthday", "phone", "email",
    "employee_id", "employer", "ahv_number"
]

HEADERS_DE = [
    "ID", "Benutzername", "Rolle", "Aktiv", "Letzter Login", "Sprache",
    "Vorname", "Nachname", "Geburtstag", "Telefon", "E-Mail",
    "Mitarbeiter-ID", "Arbeitgeber", "AHV-Nr."
]


class UserAdminDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, lang: str = "de",
                 parent=None, current_user_id: int | None = None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.lang = lang
        self.current_user_id = current_user_id

        self.setWindowTitle(
            tr("admin_users.title", self.lang)
            if tr("admin_users.title", self.lang) != "admin_users.title" else "Benutzerverwaltung"
        )

        self._build()
        self._reload()
        self.adjustSize()
        self.setSizeGripEnabled(True)
        # ausreichend breite Startgröße
        self.resize(max(self.sizeHint().width(), 1200), self.sizeHint().height())

    # ---------- UI ----------
    def _build(self):
        apply_window_controls(self)
        root = QVBoxLayout(self)

        # Suche + Buttons
        row = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText(
            tr("admin_users.search", self.lang)
            if tr("admin_users.search", self.lang) != "admin_users.search" else "Suche"
        )

        self.btn_refresh = QPushButton(
            tr("admin_users.refresh", self.lang) if tr("admin_users.refresh",
                                                       self.lang) != "admin_users.refresh" else "Aktualisieren"
        )
        self.btn_new = QPushButton(
            tr("admin_users.new", self.lang) if tr("admin_users.new", self.lang) != "admin_users.new" else "Neu"
        )
        self.btn_edit = QPushButton(
            tr("admin_users.edit", self.lang) if tr("admin_users.edit",
                                                    self.lang) != "admin_users.edit" else "Bearbeiten"
        )
        self.btn_pw = QPushButton(
            tr("admin_users.reset_pw", self.lang) if tr("admin_users.reset_pw",
                                                        self.lang) != "admin_users.reset_pw" else "Passwort zurücksetzen"
        )
        self.btn_delete = QPushButton(
            tr("admin_users.delete", self.lang) if tr("admin_users.delete",
                                                      self.lang) != "admin_users.delete" else "Löschen"
        )

        # Icons & Farben (wie im Kalender)
        self.btn_refresh.setIcon(icon("view-refresh"))
        self.btn_new.setIcon(icon("list-add"))
        self.btn_edit.setIcon(icon("document-edit"))
        self.btn_pw.setIcon(icon("dialog-password"))
        self.btn_delete.setIcon(icon("edit-delete"))

        self.btn_new.setStyleSheet("QPushButton{background:#b7f7c0;}")  # hellgrün
        self.btn_delete.setStyleSheet("QPushButton{background:#f7b7b7;}")  # hellrot
        self.btn_refresh.setStyleSheet("QPushButton{background:#b7d9f7;}")  # himmelblau
        self.btn_edit.setStyleSheet("QPushButton{background:#e0e0e0;}")  # grau
        self.btn_pw.setStyleSheet("QPushButton{background:#ffe29a;}")  # gelb

        row.addWidget(self.ed_search)
        row.addWidget(self.btn_refresh)
        row.addWidget(self.btn_new)
        row.addWidget(self.btn_edit)
        row.addWidget(self.btn_pw)
        row.addWidget(self.btn_delete)
        root.addLayout(row)

        # Tabelle
        headers = [
            "ID",
            tr("admin_users.username", self.lang) if tr("admin_users.username",
                                                        self.lang) != "admin_users.username" else "Benutzername",
            tr("admin_users.role", self.lang) if tr("admin_users.role", self.lang) != "admin_users.role" else "Rolle",
            tr("admin_users.active", self.lang) if tr("admin_users.active",
                                                      self.lang) != "admin_users.active" else "Aktiv",
            tr("admin_users.last_login", self.lang) if tr("admin_users.last_login",
                                                          self.lang) != "admin_users.last_login" else "Letzter Login",
            tr("admin_users.locale", self.lang) if tr("admin_users.locale",
                                                      self.lang) != "admin_users.locale" else "Sprache",
            tr("admin_users.first_name", self.lang) if tr("admin_users.first_name",
                                                          self.lang) != "admin_users.first_name" else "Vorname",
            tr("admin_users.last_name", self.lang) if tr("admin_users.last_name",
                                                         self.lang) != "admin_users.last_name" else "Nachname",
            tr("admin_users.birthday", self.lang) if tr("admin_users.birthday",
                                                        self.lang) != "admin_users.birthday" else "Geburtstag",
            tr("admin_users.phone", self.lang) if tr("admin_users.phone",
                                                     self.lang) != "admin_users.phone" else "Telefon",
            tr("admin_users.email", self.lang) if tr("admin_users.email",
                                                     self.lang) != "admin_users.email" else "E-Mail",
            tr("profile.employee_id", self.lang) if tr("profile.employee_id",
                                                       self.lang) != "profile.employee_id" else "Mitarbeiter-ID",
            tr("profile.employer", self.lang) if tr("profile.employer",
                                                    self.lang) != "profile.employer" else "Arbeitgeber",
            tr("profile.ahv_number", self.lang) if tr("profile.ahv_number",
                                                      self.lang) != "profile.ahv_number" else "AHV-Nr."
        ]
        self.table = QTableWidget(0, len(headers))
        vh = self.table.verticalHeader()
        vh.setVisible(False)
        vh.setSectionResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(24)
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        # Doppelklick & Kontextmenü
        self.table.itemDoubleClicked.connect(lambda *_: self._open_edit())
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._open_ctx_menu)

        # Signals
        self.btn_refresh.clicked.connect(self._reload)
        self.btn_new.clicked.connect(self._new)
        self.btn_edit.clicked.connect(self._edit_selected)
        self.btn_pw.clicked.connect(self._reset_password_selected)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.ed_search.textChanged.connect(self._reload)

    # ---------- Daten laden ----------
    def _reload(self):
        query = (self.ed_search.text() or "").strip().lower()

        with self.session_factory() as s:
            # nur eindeutige, „echte“ Benutzer; skippe leere Usernamen
            users = [
                u for u in s.execute(select(User).order_by(User.id.asc())).scalars().all()
                if (u.username or "").strip() != ""
            ]
            profs = {p.user_id: p for p in s.execute(select(UserProfile)).scalars().all()}

        self.table.setRowCount(0)

        seen_ids: set[int] = set()  # Sicherheitsnetz gegen dublette Anzeige
        for u in users:
            if u.id in seen_ids:
                continue
            seen_ids.add(u.id)

            p = profs.get(u.id)

            # Textfilter
            hay = " ".join([
                u.username or "",
                (p.first_name or "") if p else "",
                (p.last_name or "") if p else "",
                (p.email or "") if p else "",
                (p.employer or "") if p else "",
            ]).lower()
            if query and query not in hay:
                continue

            # Formatierungen
            ll = getattr(u, "last_login", None)
            if isinstance(ll, _dt):
                last_login_txt = ll.strftime("%Y-%m-%d %H:%M")
            else:
                last_login_txt = str(ll) if ll else ""

            bday_txt = ""
            if p and getattr(p, "birthday", None):
                if isinstance(p.birthday, _date):
                    bday_txt = p.birthday.strftime("%Y-%m-%d")
                else:
                    bday_txt = str(p.birthday)

            # Zeile füllen
            row_vals = [""] * len(HEADERS)
            row_vals[COL_ID] = str(u.id)
            row_vals[COL_USERNAME] = u.username or ""
            row_vals[COL_ROLE] = (u.role or "").upper()
            row_vals[COL_ACTIVE] = "1" if getattr(u, "is_active", getattr(u, "active", True)) else "0"
            row_vals[COL_LASTLOGIN] = last_login_txt
            row_vals[COL_LOCALE] = (p.locale if p else "") or ""
            row_vals[COL_FIRST] = (p.first_name if p else "") or ""
            row_vals[COL_LAST] = (p.last_name if p else "") or ""
            row_vals[COL_BDAY] = bday_txt
            row_vals[COL_PHONE] = (p.phone or "") if p else ""
            row_vals[COL_EMAIL] = (p.email or "") if p else ""
            row_vals[COL_EMP_ID] = (str(p.employee_id) if (p and p.employee_id is not None) else "")
            row_vals[COL_EMPLOYER] = (p.employer or "") if p else ""
            row_vals[COL_AHV] = (getattr(p, "ahv_number", "") if p else "")

            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, val in enumerate(row_vals):
                it = QTableWidgetItem(val)
                if c == COL_ID:
                    it.setData(Qt.UserRole, u.id)  # ID mitschleppen
                self.table.setItem(r, c, it)

        self.table.resizeColumnsToContents()

    # ---------- Aktionen ----------
    def _selected_ids(self) -> list[int]:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        out: list[int] = []
        for r in rows:
            it = self.table.item(r, COL_ID)
            if it and it.data(Qt.UserRole) is not None:
                out.append(int(it.data(Qt.UserRole)))
        return out

    def _current_user_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        it = self.table.item(r, COL_ID)
        return int(it.data(Qt.UserRole)) if it else None

    def _new(self):
        dlg = RegistrationDialog(self.session_factory, lang=self.lang, parent=self)
        if dlg.exec():
            self._reload()

    def _edit_selected(self):
        ids = self._selected_ids()
        if not ids:
            return
        for uid in ids:
            dlg = UserEditDialog(self.session_factory, user_id=uid, lang=self.lang, parent=self)
            dlg.exec()
        self._reload()

    def _delete_selected(self):
        ids = self._selected_ids()
        if not ids:
            return
        if QMessageBox.question(
                self, self.windowTitle(),
                f"{len(ids)} {tr('admin_users.delete', self.lang) if tr('admin_users.delete', self.lang) != 'admin_users.delete' else 'löschen'}?"
        ) != QMessageBox.StandardButton.Yes:
            return
        with self.session_factory() as s:
            for uid in ids:
                delete_user(s, uid)
        self._reload()

    def _reset_password_selected(self):
        ids = self._selected_ids()
        if not ids:
            return

        from PySide6.QtWidgets import QInputDialog
        from core.services.auth_service import hash_password  # robust, überall verfügbar

        for uid in ids:
            new_pw, ok = QInputDialog.getText(
                self,
                tr("admin_users.reset_pw", self.lang) if tr("admin_users.reset_pw",
                                                            self.lang) != "admin_users.reset_pw" else "Passwort zurücksetzen",
                f"Neues Passwort für Benutzer-ID {uid}:"
            )
            if not ok or not new_pw:
                continue

            with self.session_factory() as s:
                u = s.execute(select(User).where(User.id == uid)).scalar_one_or_none()
                if not u:
                    continue
                u.password_hash = hash_password(new_pw)
                if hasattr(u, "must_change_password"):
                    u.must_change_password = True
                s.commit()

        QMessageBox.information(self, self.windowTitle(), "Passwort geändert.")

    # ---------- Doppelklick & Kontextmenü ----------
    def _open_edit(self):
        uid = self._current_user_id()
        if not uid:
            return
        dlg = UserEditDialog(self.session_factory, user_id=uid, lang=self.lang, parent=self)
        if dlg.exec():
            self._reload()

    def _open_ctx_menu(self, pos):
        idx = self.table.indexAt(pos)
        if idx.isValid():
            self.table.selectRow(idx.row())

        m = QMenu(self)
        a_new = m.addAction(icon("list-add"),
                            tr("admin_users.new", self.lang) if tr("admin_users.new",
                                                                   self.lang) != "admin_users.new" else "Neu")
        a_edit = m.addAction(icon("document-edit"),
                             tr("admin_users.edit", self.lang) if tr("admin_users.edit",
                                                                     self.lang) != "admin_users.edit" else "Bearbeiten")
        a_pw = m.addAction(icon("dialog-password"),
                           tr("admin_users.reset_pw", self.lang) if tr("admin_users.reset_pw",
                                                                       self.lang) != "admin_users.reset_pw" else "Passwort zurücksetzen")
        a_del = m.addAction(icon("edit-delete"),
                            tr("admin_users.delete", self.lang) if tr("admin_users.delete",
                                                                      self.lang) != "admin_users.delete" else "Löschen")
        m.addSeparator()
        a_ref = m.addAction(icon("view-refresh"),
                            tr("admin_users.refresh", self.lang) if tr("admin_users.refresh",
                                                                       self.lang) != "admin_users.refresh" else "Aktualisieren")

        act = m.exec(self.table.viewport().mapToGlobal(pos))
        if not act:
            return
        if act == a_new:
            self._new()
        elif act == a_edit:
            self._open_edit()
        elif act == a_pw:
            self._reset_password_selected()
        elif act == a_del:
            self._delete_selected()
        elif act == a_ref:
            self._reload()
