from typing import Optional
import sqlite3

class SubscriptionStore:

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_by_user_id(self, user_id: str) -> Optional[dict]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT plan, status
            FROM subscriptions
            WHERE user_id = ?
        """, (user_id,))
        row = cur.fetchone()

        if not row:
            return None

        return {
            "plan": row[0],
            "status": row[1]
        }
