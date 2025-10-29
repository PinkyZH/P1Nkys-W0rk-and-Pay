# core/db_migrate.py
from __future__ import annotations

from contextlib import closing

# Liste von (tabelle, spaltenname, sql_type, backfill_sql_optional)
# Hinweis: SQLite speichert unsere verschlüsselten Strings/Texts ohnehin als TEXT/BLOB;
# für neue Spalten reicht TEXT.
MISSING_COLUMNS = [
    # user_profiles.postal_code neu, ggf. aus alter Spalte 'postcode' befüllen
    ("user_profiles", "postal_code", "TEXT",
     "UPDATE user_profiles SET postal_code = postcode WHERE postal_code IS NULL AND postcode IS NOT NULL"),
    # (Beispiele für weitere Felder – auskommentiert lassen, falls du sie später brauchst)
    # ("user_profiles", "bank_zip", "TEXT", None),
    # ("user_profiles", "bank_city", "TEXT", None),
    # ("user_profiles", "bank_country", "TEXT", None),
]


def _table_has_column(conn, table: str, col: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]  # r[1] = name
    return col in cols


def _add_column(conn, table: str, col: str, sql_type: str) -> None:
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sql_type}")


def _safe_exec(conn, sql: str) -> None:
    if not sql:
        return
    try:
        conn.execute(sql)
    except Exception:
        # Backfill ist optional – nicht hart fehlschlagen
        pass


def run_light_migrations(engine) -> None:
    """Führt kleine, idempotente SQLite-Migrationen aus (nur ADD COLUMN + optionale Backfills)."""
    with closing(engine.raw_connection()) as raw:
        conn = raw.cursor()
        try:
            for table, col, sql_type, backfill in MISSING_COLUMNS:
                if not _table_has_column(conn, table, col):
                    _add_column(conn, table, col, sql_type)
                    _safe_exec(conn, backfill)
            raw.commit()
        finally:
            conn.close()
