"""Persistent preference and consent storage with TTL and hashing.

This module provides a SQLite-backed store for user preferences with
optional expiry (TTL).  It also implements a consent store and helper
functions for generating hashed user identifiers with a salt.
"""
from __future__ import annotations
import os
import sqlite3
import time
import hashlib
from typing import Optional, Dict

DEFAULT_DB_PATH = os.environ.get("UIRE_DB", "preferences.db")
DEFAULT_SALT = os.environ.get("UIRE_SALT", "uire_salt")

class PreferenceStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            # preferences table with expiry and hashed key support
            cur.execute(
                """CREATE TABLE IF NOT EXISTS preferences (
                    user_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    expires_at INTEGER,
                    PRIMARY KEY(user_id, key)
                );"""
            )
            # consent table
            cur.execute(
                """CREATE TABLE IF NOT EXISTS consent (
                    user_id TEXT PRIMARY KEY,
                    accepted INTEGER NOT NULL,
                    ts INTEGER NOT NULL
                );"""
            )
            con.commit()
        finally:
            con.close()

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def set(self, user_id: str, key: str, value: str, ttl_ms: Optional[int] = None) -> None:
        exp = None if ttl_ms is None else (self._now_ms() + ttl_ms)
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute(
                """INSERT INTO preferences(user_id,key,value,expires_at)
                    VALUES(?,?,?,?)
                    ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value, expires_at=excluded.expires_at""",
                (user_id, key, value, exp),
            )
            con.commit()
        finally:
            con.close()

    def get(self, user_id: str, key: str) -> Optional[str]:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute("SELECT value, expires_at FROM preferences WHERE user_id=? AND key=?", (user_id, key))
            row = cur.fetchone()
            if not row:
                return None
            value, exp = row
            if exp is not None and exp < self._now_ms():
                cur.execute("DELETE FROM preferences WHERE user_id=? AND key=?", (user_id, key))
                con.commit()
                return None
            return value
        finally:
            con.close()

    def all_for_user(self, user_id: str) -> Dict[str, str]:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute("SELECT key, value, expires_at FROM preferences WHERE user_id=?", (user_id,))
            out = {}
            stale = []
            for k, v, exp in cur.fetchall():
                if exp is not None and exp < self._now_ms():
                    stale.append(k)
                else:
                    out[k] = v
            for k in stale:
                cur.execute("DELETE FROM preferences WHERE user_id=? AND key=?", (user_id, k))
            con.commit()
            return out
        finally:
            con.close()

    def clear_user(self, user_id: str) -> None:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute("DELETE FROM preferences WHERE user_id=?", (user_id,))
            con.commit()
        finally:
            con.close()

class ConsentStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute(
                """CREATE TABLE IF NOT EXISTS consent (
                    user_id TEXT PRIMARY KEY,
                    accepted INTEGER NOT NULL,
                    ts INTEGER NOT NULL
                );"""
            )
            con.commit()
        finally:
            con.close()

    def set(self, user_id: str, accepted: bool) -> None:
        ts = int(time.time() * 1000)
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute(
                """INSERT INTO consent(user_id, accepted, ts)
                    VALUES(?,?,?)
                    ON CONFLICT(user_id) DO UPDATE SET accepted=excluded.accepted, ts=excluded.ts""",
                (user_id, 1 if accepted else 0, ts),
            )
            con.commit()
        finally:
            con.close()

    def get(self, user_id: str) -> bool:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute("SELECT accepted FROM consent WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            return bool(row[0]) if row else False
        finally:
            con.close()

# Helper for hashed IDs

def hashed_id(raw: str, salt: str = DEFAULT_SALT) -> str:
    return hashlib.sha256(f"{raw}|{salt}".encode()).hexdigest()[:16]
