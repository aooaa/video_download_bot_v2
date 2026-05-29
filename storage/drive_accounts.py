from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DriveAccount:
    telegram_user_id: int
    provider: str
    remote_name: str
    upload_path: str
    enabled: bool = True


class DriveAccountStore:
    def __init__(self, db_path: str | Path = "bot_settings.db") -> None:
        self.db_path = Path(db_path)
        self.init_db()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS drive_accounts (
                    telegram_user_id INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    remote_name TEXT NOT NULL,
                    upload_path TEXT NOT NULL DEFAULT 'Downloads',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (telegram_user_id, provider)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    telegram_user_id INTEGER PRIMARY KEY,
                    default_provider TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def upsert_account(self, account: DriveAccount) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO drive_accounts (
                    telegram_user_id, provider, remote_name, upload_path, enabled, updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_user_id, provider) DO UPDATE SET
                    remote_name=excluded.remote_name,
                    upload_path=excluded.upload_path,
                    enabled=excluded.enabled,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    account.telegram_user_id,
                    account.provider,
                    account.remote_name,
                    account.upload_path,
                    1 if account.enabled else 0,
                ),
            )

    def get_account(self, telegram_user_id: int, provider: str) -> DriveAccount | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT telegram_user_id, provider, remote_name, upload_path, enabled
                FROM drive_accounts
                WHERE telegram_user_id = ? AND provider = ? AND enabled = 1
                """,
                (telegram_user_id, provider),
            ).fetchone()
        if not row:
            return None
        return DriveAccount(row[0], row[1], row[2], row[3], bool(row[4]))

    def list_accounts(self, telegram_user_id: int) -> list[DriveAccount]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT telegram_user_id, provider, remote_name, upload_path, enabled
                FROM drive_accounts
                WHERE telegram_user_id = ?
                ORDER BY provider
                """,
                (telegram_user_id,),
            ).fetchall()
        return [DriveAccount(row[0], row[1], row[2], row[3], bool(row[4])) for row in rows]

    def set_upload_path(self, telegram_user_id: int, provider: str, upload_path: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE drive_accounts
                SET upload_path = ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_user_id = ? AND provider = ?
                """,
                (upload_path, telegram_user_id, provider),
            )
            return cursor.rowcount > 0

    def delete_account(self, telegram_user_id: int, provider: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM drive_accounts WHERE telegram_user_id = ? AND provider = ?",
                (telegram_user_id, provider),
            )
            return cursor.rowcount > 0
