"""Accounts and progress, in SQLite.

Progress is keyed by (user, module, "<lesson-slug>/<step-index>"), so every kind of
step (explain, try-it, exercise, quiz) is tracked the same way.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

USERNAME = re.compile(r"^[a-z0-9_-]{3,32}$")
MIN_PASSWORD = 8

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash BLOB NOT NULL,
    salt BLOB NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS progress (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id TEXT NOT NULL,
    step_ref TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    hints_used INTEGER NOT NULL DEFAULT 0,
    showed_solution INTEGER NOT NULL DEFAULT 0,
    updated REAL NOT NULL,
    PRIMARY KEY (user_id, module_id, step_ref)
);
"""


class AuthError(ValueError):
    pass


@dataclass
class User:
    id: int
    username: str


@dataclass
class StepProgress:
    done: bool
    attempts: int
    hints_used: int
    showed_solution: bool


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def _db(self):
        # One short-lived connection per operation keeps this safe across threads.
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA foreign_keys = ON")
            with db:
                yield db

    # --- accounts --------------------------------------------------------------

    def register(self, username: str, password: str) -> User:
        username = username.strip().lower()
        if not USERNAME.match(username):
            raise AuthError("Usernames are 3-32 characters: letters, numbers, - and _")
        if len(password) < MIN_PASSWORD:
            raise AuthError(f"Passwords need at least {MIN_PASSWORD} characters")
        salt = secrets.token_bytes(16)
        try:
            with self._db() as db:
                cursor = db.execute(
                    "INSERT INTO users (username, password_hash, salt, created) "
                    "VALUES (?, ?, ?, ?)",
                    (username, _hash(password, salt), salt, time.time()),
                )
        except sqlite3.IntegrityError:
            raise AuthError("That username is taken") from None
        return User(cursor.lastrowid, username)

    def authenticate(self, username: str, password: str) -> User:
        with self._db() as db:
            row = db.execute(
                "SELECT id, username, password_hash, salt FROM users WHERE username = ?",
                (username.strip().lower(),),
            ).fetchone()
        if row is None or not hmac.compare_digest(row[2], _hash(password, row[3])):
            raise AuthError("Wrong username or password")
        return User(row[0], row[1])

    def create_token(self, user: User) -> str:
        token = secrets.token_urlsafe(32)
        with self._db() as db:
            db.execute(
                "INSERT INTO tokens (token, user_id, created) VALUES (?, ?, ?)",
                (token, user.id, time.time()),
            )
        return token

    def user_for_token(self, token: str) -> User | None:
        with self._db() as db:
            row = db.execute(
                "SELECT users.id, users.username FROM tokens "
                "JOIN users ON users.id = tokens.user_id WHERE token = ?",
                (token,),
            ).fetchone()
        return User(*row) if row else None

    def revoke_token(self, token: str) -> None:
        with self._db() as db:
            db.execute("DELETE FROM tokens WHERE token = ?", (token,))

    # --- progress --------------------------------------------------------------

    def record(
        self,
        user: User,
        module_id: str,
        step_ref: str,
        *,
        done: bool = False,
        attempt: bool = False,
        hints_used: int = 0,
        showed_solution: bool = False,
    ) -> None:
        """Merge an event into a step's progress. Nothing is ever un-done."""
        with self._db() as db:
            db.execute(
                """
                INSERT INTO progress
                    (user_id, module_id, step_ref, done, attempts, hints_used,
                     showed_solution, updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (user_id, module_id, step_ref) DO UPDATE SET
                    done = MAX(done, excluded.done),
                    attempts = attempts + excluded.attempts,
                    hints_used = MAX(hints_used, excluded.hints_used),
                    showed_solution = MAX(showed_solution, excluded.showed_solution),
                    updated = excluded.updated
                """,
                (
                    user.id,
                    module_id,
                    step_ref,
                    int(done),
                    int(attempt),
                    hints_used,
                    int(showed_solution),
                    time.time(),
                ),
            )

    def progress(self, user: User, module_id: str) -> dict[str, StepProgress]:
        with self._db() as db:
            rows = db.execute(
                "SELECT step_ref, done, attempts, hints_used, showed_solution FROM progress "
                "WHERE user_id = ? AND module_id = ?",
                (user.id, module_id),
            ).fetchall()
        return {
            ref: StepProgress(bool(done), attempts, hints, bool(showed))
            for ref, done, attempts, hints, showed in rows
        }


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
