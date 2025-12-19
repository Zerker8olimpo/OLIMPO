# backend/database/device_store.py
from datetime import datetime
from backend.database.connection import get_connection


def get_device_by_user(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM devices WHERE user_id = ? ORDER BY last_seen DESC LIMIT 1",
        (user_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row


def register_device(user_id: int, device_uuid: str, platform: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO devices (user_id, device_uuid, platform, created_at, last_seen)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, device_uuid, platform, datetime.utcnow(), datetime.utcnow())
    )
    conn.commit()
    conn.close()


def touch_device(device_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE devices SET last_seen = ? WHERE id = ?",
        (datetime.utcnow(), device_id)
    )
    conn.commit()
    conn.close()


def delete_devices_by_user(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM devices WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
