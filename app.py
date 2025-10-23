from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication, QDialog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db import init_db
from core.services.auth_service import ensure_default_admin
from core.services.user_service import ensure_wage_defaults

from ui.login_view import LoginDialog
from ui.main_window import MainWindow
from core.services.settings_service import get_lang
from core.services.log_service import setup_logging
setup_logging()

DB_URL = "sqlite:///workpay.db"

import logging, logging.handlers, os
LOG_DIR = "logs"; os.makedirs(LOG_DIR, exist_ok=True)
handler = logging.handlers.RotatingFileHandler(os.path.join(LOG_DIR, "app.log"), maxBytes=1_000_000, backupCount=5, encoding="utf-8")
logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("workpay")

# und später z. B.:
logger.info("App gestartet (v%s)", APP_VERSION if 'APP_VERSION' in globals() else "?")

def init_engine_and_session(db_url: str = DB_URL):
    """Engine + Session initialisieren"""
    engine = create_engine(db_url, echo=False, future=True)
    init_db(engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
        expire_on_commit=False,
    )

    with Session() as s:
        ensure_default_admin(s)
        ensure_wage_defaults(s)

    return engine, Session

def main() -> int:
    app = QApplication(sys.argv)
    engine, Session = init_engine_and_session()

    while True:
        lang = get_lang()
        login = LoginDialog(Session)
        if login.exec() != QDialog.Accepted:
            return 0

        user = login.get_logged_in_user()
        lang = login.get_current_language()

        mw = MainWindow(Session, user_id=user.id, username=user.username, lang=lang)
        did_logout = {"flag": False}
        def _on_logout(): did_logout["flag"]=True; mw.close()
        mw.logoutRequested.connect(_on_logout)
        mw.show()
        app.exec()

        if did_logout["flag"]:
            continue
        break
    return 0

if __name__ == "__main__":
    sys.exit(main())
