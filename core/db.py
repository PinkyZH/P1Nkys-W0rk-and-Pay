from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _has_column(conn, table: str, column: str) -> bool:
    try:
        res = conn.exec_driver_sql(f"PRAGMA table_info({table})").all()
    except Exception:
        return False
    return any(r[1] == column for r in res)


def init_db(engine):
    # Tabellen anlegen (für neue DBs)
    Base.metadata.create_all(engine)

    # Bestehende SQLite-DBs „sanft“ nachrüsten
    try:
        _ensure_sqlite_columns(engine)
    except Exception as ex:
        # nicht abstürzen lassen; im Log vermerken
        import logging
        logging.getLogger("workpay").warning("Schema-Nachrüstung übersprungen: %s", ex)

    # ---- defensive Nachrüstung für Bestandsdatenbanken ----
    with engine.begin() as conn:
        # bereits vorhandene (deine bisherigen) Lohnspalten – ggf. nachrüsten
        for tbl, col, ddl in [
            ("user_profiles", "hourly_brutto", "FLOAT"),
            ("user_profiles", "vac_pct", "FLOAT"),
            ("user_profiles", "holiday_pct", "FLOAT"),
            ("user_profiles", "thirteenth_pct", "FLOAT"),
            ("user_profiles", "expenses_per_hour", "FLOAT"),
            ("user_profiles", "ahv_pct", "FLOAT"),
            ("user_profiles", "nbu_pct", "FLOAT"),
            ("user_profiles", "ktg_pct", "FLOAT"),
            ("user_profiles", "bvg_pct", "FLOAT"),
            ("user_profiles", "lgav_fixed_monthly", "FLOAT"),
            ("user_profiles", "weekly_hours", "FLOAT"),
        ]:
            if not _has_column(conn, tbl, col):
                conn.exec_driver_sql(f"ALTER TABLE {tbl} ADD COLUMN {col} {ddl}")

        # AHV-Nummer in user_profiles nachrüsten
        if not _has_column(conn, "user_profiles", "ahv_number"):
            conn.exec_driver_sql("ALTER TABLE user_profiles ADD COLUMN ahv_number VARCHAR(64)")

        # Legacy-Feld hourly_rate nach hourly_brutto migrieren (falls vorhanden)
        if _has_column(conn, "user_profiles", "hourly_rate") and _has_column(conn, "user_profiles", "hourly_brutto"):
            conn.exec_driver_sql("UPDATE user_profiles SET hourly_brutto = COALESCE(hourly_brutto, hourly_rate)")


def get_engine(url="sqlite:///workpay.db"):
    return create_engine(url, echo=False, future=True)


def get_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _ensure_sqlite_columns(engine):
    """Fügt fehlende Spalten in bestehenden SQLite-Tabellen hinzu (leichtgewichtig, ohne Alembic)."""
    with engine.begin() as conn:
        def has_col(table: str, col: str) -> bool:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            cols = {r[1] for r in rows}  # r[1] = name
            return col in cols

        # work_entries: optionale Felder nachrüsten
        if not has_col("work_entries", "hourly_override"):
            conn.execute(text("ALTER TABLE work_entries ADD COLUMN hourly_override REAL"))
        if not has_col("work_entries", "pay_rate_override"):
            conn.execute(text("ALTER TABLE work_entries ADD COLUMN pay_rate_override REAL"))
        if not has_col("work_entries", "overtime_hours"):
            conn.execute(text("ALTER TABLE work_entries ADD COLUMN overtime_hours REAL"))
