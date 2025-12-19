# backend/database/device_conflict_store.py
from datetime import datetime
from backend.database.connection import get_connection


def log_conflict(user_id: int, device_uuid: str, ip_address: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO device_conflicts_log (user_id, attempt_device_id, ip_address, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, device_uuid, ip_address, datetime.utcnow())
    )
    conn.commit()
    conn.close()
