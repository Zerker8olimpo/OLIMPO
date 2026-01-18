# backend/scripts/migrate_001_billing.py
import sqlite3
from backend.api.settings import settings

def main():
    if not settings.DATABASE_URL.startswith("sqlite"):
        print("[MIGRATE] Este script está hecho para SQLite. Para Postgres, usa ALTER TABLE equivalente.")
        return

    path = settings.DATABASE_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    # Agregar columnas si no existen
    def add_column(table: str, col_def: str):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            print(f"[MIGRATE] OK: {table} + {col_def}")
        except Exception as e:
            print(f"[MIGRATE] SKIP: {table} {col_def} ({e})")

    add_column("subscriptions", "provider TEXT DEFAULT 'google' NOT NULL")
    add_column("subscriptions", "external_reference TEXT")

    # Crear payments si no existe
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        amount INTEGER NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL,
        external_id TEXT,
        created_at TEXT
    );
    """)

    conn.commit()
    conn.close()
    print("[MIGRATE] Done.")

if __name__ == "__main__":
    main()
