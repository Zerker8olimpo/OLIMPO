# backend/database/init_db.py
from backend.database.connection import get_connection


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_devices (
        user_id TEXT PRIMARY KEY,
        device_id TEXT NOT NULL,
        registered_at TEXT,
        last_login TEXT,
        is_active INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS device_conflicts_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        attempt_device_id TEXT,
        ip_address TEXT,
        timestamp TEXT
    );
    """)

    conn.commit()
    conn.close()

    print("✔ Base de datos inicializada correctamente")


if __name__ == "__main__":
    init_db()
