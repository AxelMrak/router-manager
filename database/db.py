from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path


class LocalDatabase:
    """SQLite database for local app data."""

    def __init__(self) -> None:
        self.db_path = self._get_db_path()
        self._init_db()

    def _get_db_path(self) -> Path:
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base = Path.home() / ".config"
        db_dir = base / "router-manager"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "local.db"

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS device_aliases (
                    mac TEXT PRIMARY KEY,
                    alias TEXT NOT NULL,
                    is_guest INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS cached_devices (
                    mac TEXT PRIMARY KEY,
                    last_ip TEXT,
                    last_seen TEXT,
                    data TEXT
                );

                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    # --- Device aliases ---

    def get_aliases(self) -> dict[str, str]:
        """Get all device aliases as a dictionary."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT mac, alias FROM device_aliases")
            return {row["mac"]: row["alias"] for row in cursor.fetchall()}
        finally:
            conn.close()

    def set_alias(self, mac: str, alias: str) -> None:
        """Set or update an alias for a device."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO device_aliases (mac, alias) VALUES (?, ?)",
                (mac.upper(), alias),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_alias(self, mac: str) -> None:
        """Delete an alias for a device."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM device_aliases WHERE mac = ?", (mac.upper(),))
            conn.commit()
        finally:
            conn.close()

    # --- Guest flags ---

    def get_guest_macs(self) -> list[str]:
        """Get all MAC addresses marked as guests."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT mac FROM device_aliases WHERE is_guest = 1"
            )
            return [row["mac"] for row in cursor.fetchall()]
        finally:
            conn.close()

    def set_guest(self, mac: str, is_guest: bool) -> None:
        """Set or update the guest flag for a device."""
        conn = self._get_conn()
        try:
            # Ensure the record exists first
            conn.execute(
                "INSERT OR IGNORE INTO device_aliases (mac, alias, is_guest) VALUES (?, '', ?)",
                (mac.upper(), 1 if is_guest else 0),
            )
            conn.execute(
                "UPDATE device_aliases SET is_guest = ? WHERE mac = ?",
                (1 if is_guest else 0, mac.upper()),
            )
            conn.commit()
        finally:
            conn.close()

    # --- Cached devices ---

    def cache_device(self, mac: str, ip: str, data: dict) -> None:
        """Cache device information."""
        from datetime import datetime

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO cached_devices
                   (mac, last_ip, last_seen, data)
                   VALUES (?, ?, ?, ?)""",
                (mac.upper(), ip, datetime.now().isoformat(), json.dumps(data)),
            )
            conn.commit()
        finally:
            conn.close()

    def get_cached_devices(self) -> list[dict]:
        """Get all cached devices."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT * FROM cached_devices")
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append(
                    {
                        "mac": row["mac"],
                        "last_ip": row["last_ip"],
                        "last_seen": row["last_seen"],
                        "data": json.loads(row["data"]) if row["data"] else {},
                    }
                )
            return result
        finally:
            conn.close()

    # --- Generic key-value state ---

    def get_state(self, key: str, default: str | None = None) -> str | None:
        """Get a state value by key."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT value FROM app_state WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            return row["value"] if row else default
        finally:
            conn.close()

    def set_state(self, key: str, value: str) -> None:
        """Set a state value."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
        finally:
            conn.close()
