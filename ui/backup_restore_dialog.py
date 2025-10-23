from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from config import APP_NAME
from core.services.backup_service import create_backup, restore_backup
from core.utils.files import DATA_DIR  # Avatars
import os
from core.services.log_service import log_activity, log_error
from core.utils.i18n import t

class BackupRestoreDialog(QDialog):
    def __init__(self, session_factory: sessionmaker, db_url: str, current_user_id: int, is_admin: bool, lang: str = "de", parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.db_url = db_url; self.user_id = current_user_id; self.is_admin = is_admin; self.lang = lang
        self.setWindowTitle(t("tools.backup_restore", self.lang) if t("tools.backup_restore", self.lang)!="tools.backup_restore" else "Backup / Restore")
        self.setSizeGripEnabled(True); self._build(); self.adjustSize()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(t("tools.backup_desc", self.lang) if t("tools.backup_desc", self.lang)!="tools.backup_desc" else
            "Backup: erstellt ein ZIP mit DB + Avatars + Konfiguration.\nRestore: stellt aus ZIP wieder her (Admin-only)."))
        row = QHBoxLayout()
        btn_backup = QPushButton(t("tools.backup_btn", self.lang) if t("tools.backup_btn", self.lang)!="tools.backup_btn" else "Backup erstellen …")
        btn_restore = QPushButton(t("tools.restore_btn", self.lang) if t("tools.restore_btn", self.lang)!="tools.restore_btn" else "Restore …")
        row.addWidget(btn_backup); row.addWidget(btn_restore); layout.addLayout(row)
        btn_backup.clicked.connect(self._do_backup); btn_restore.clicked.connect(self._do_restore)
        if not self.is_admin: btn_restore.setEnabled(False)

    def _config_files(self) -> list[Path]:
        # du kannst hier weitere Dateien aufnehmen
        base = Path(os.path.dirname(os.path.dirname(__file__))).parent
        return [base / "config.py", base / "languages.py"]

    def _do_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, t("tools.backup_btn", self.lang), "backup.zip", "ZIP (*.zip)")
        if not path: return
        out = Path(path)
        with self.session_factory() as s:
            try:
                create_backup(s, self.db_url, Path(DATA_DIR), [], out, self.user_id)
                QMessageBox.information(self, t("tools.backup_restore", self.lang), t("tools.backup_ok", self.lang).format(path=str(out)) if t("tools.backup_ok", self.lang)!="tools.backup_ok" else f"Backup gespeichert: {out}")
                log_activity(self.user_id, "backup.create", {"file": str(out)})
            except Exception as ex:
                QMessageBox.critical(self, t("tools.backup_restore", self.lang), str(ex)); log_error("Fehler beim Backup", exc=ex)

    def _do_restore(self):
        if not self.is_admin:
            QMessageBox.warning(self, t("tools.backup_restore", self.lang), "Nur ADMIN darf Restore ausführen."); return
        path, _ = QFileDialog.getOpenFileName(self, t("tools.restore_btn", self.lang), "", "ZIP (*.zip)")
        if not path: return
        if QMessageBox.question(self, t("tools.backup_restore", self.lang), t("tools.restore_warn", self.lang) if t("tools.restore_warn", self.lang)!="tools.restore_warn" else "Achtung: Daten werden überschrieben. Fortfahren?") != QMessageBox.StandardButton.Yes:
            return
        with self.session_factory() as s:
            try:
                restore_backup(s, self.db_url, Path(DATA_DIR), Path(path), self.user_id)
                QMessageBox.information(self, t("tools.backup_restore", self.lang), t("tools.restore_ok", self.lang) if t("tools.restore_ok", self.lang)!="tools.restore_ok" else "Wiederherstellung abgeschlossen. Bitte Anwendung neu starten.")
                log_activity(self.user_id, "backup.restore", {"file": path})
            except Exception as ex:
                QMessageBox.critical(self, t("tools.backup_restore", self.lang), str(ex)); log_error("Fehler beim Wiederherstellen", exc=ex)