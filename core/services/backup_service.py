from __future__ import annotations

import shutil
import time
import zipfile
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from .audit_service import log_action


# DB-URL ist in app.py als sqlite:///workpay.db – wir leiten den Pfad ab
def _sqlite_path_from_url(db_url: str) -> Path:
    # erwartet sqlite:///absolute/relative/path
    if not db_url.startswith("sqlite:///"):
        raise RuntimeError("Nur sqlite wird vom Backup-Service unterstützt.")
    p = db_url.replace("sqlite:///", "", 1)
    return Path(p).resolve()


def create_backup(session: Session, db_url: str, avatars_dir: Path, config_files: list[Path], out_zip: Path,
                  user_id: Optional[int]) -> Path:
    out_zip = out_zip.resolve()
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    db_file = _sqlite_path_from_url(db_url)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        # DB
        z.write(db_file, arcname="db/workpay.db")
        # Avatars
        if avatars_dir.exists():
            for p in avatars_dir.rglob("*"):
                if p.is_file():
                    z.write(p, arcname=str(Path("avatars") / p.name))
        # Konfigurationen
        for cf in config_files:
            if cf.exists():
                z.write(cf, arcname=f"config/{cf.name}")
        # kleines Manifest
        manifest = f"created:{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        z.writestr("MANIFEST.txt", manifest)
    log_action(session, user_id, "BACKUP", "System", after={"file": str(out_zip)})
    return out_zip


def restore_backup(session: Session, db_url: str, avatars_dir: Path, zip_file: Path, user_id: Optional[int]) -> None:
    """Achtung: überschreibt DB & Avatars aus ZIP."""
    db_file = _sqlite_path_from_url(db_url)
    zip_file = zip_file.resolve()
    if not zip_file.exists():
        raise FileNotFoundError(zip_file)

    tmp_dir = Path(zip_file).parent / f".tmp_restore_{int(time.time())}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_file, "r") as z:
            z.extractall(tmp_dir)
        # DB ersetzen
        src_db = tmp_dir / "db" / "workpay.db"
        if src_db.exists():
            if db_file.exists():
                shutil.copy2(db_file, db_file.with_suffix(".bak"))
            shutil.copy2(src_db, db_file)
        # Avatars ersetzen
        src_avatars = tmp_dir / "avatars"
        if src_avatars.exists():
            avatars_dir.mkdir(parents=True, exist_ok=True)
            for p in avatars_dir.glob("*"):
                if p.is_file():
                    p.unlink()
            for p in src_avatars.glob("*"):
                if p.is_file():
                    shutil.copy2(p, avatars_dir / p.name)
        log_action(session, user_id, "RESTORE", "System", after={"file": str(zip_file)})
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
