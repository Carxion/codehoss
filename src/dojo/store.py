"""Accounts and progress, in SQLite.

Progress is keyed by (user, module, "<lesson-slug>/<step-index>"), so every kind of
step (explain, try-it, exercise, quiz) is tracked the same way.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

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
CREATE TABLE IF NOT EXISTS ai_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT,
    model TEXT,
    api_key_encrypted BLOB
);
CREATE TABLE IF NOT EXISTS project_levels (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id TEXT NOT NULL,
    lesson_slug TEXT NOT NULL,
    level TEXT NOT NULL,
    PRIMARY KEY (user_id, module_id, lesson_slug)
);
CREATE TABLE IF NOT EXISTS submissions (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exercise_id TEXT NOT NULL,
    code TEXT NOT NULL,
    passed_at REAL NOT NULL,
    PRIMARY KEY (user_id, exercise_id)
);
CREATE TABLE IF NOT EXISTS progress (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_id TEXT NOT NULL,
    step_ref TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    hints_used INTEGER NOT NULL DEFAULT 0,
    showed_solution INTEGER NOT NULL DEFAULT 0,
    tutor_questions INTEGER NOT NULL DEFAULT 0,
    updated REAL NOT NULL,
    PRIMARY KEY (user_id, module_id, step_ref)
);
"""

# Columns added after a table was first created: (table, column, definition).
MIGRATIONS = [
    ("progress", "tutor_questions", "INTEGER NOT NULL DEFAULT 0"),
]


class AuthError(ValueError):
    pass


@dataclass
class User:
    id: int
    username: str


@dataclass
class AISettingsRow:
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None


@dataclass
class StepProgress:
    done: bool
    attempts: int
    hints_used: int
    showed_solution: bool
    tutor_questions: int = 0


class Store:
    def __init__(self, path: Path | str, secret_key: bytes | None = None):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(secret_key or _load_secret(Path(self.path)))
        with self._db() as db:
            db.executescript(SCHEMA)
            for table, column, definition in MIGRATIONS:
                columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                if column not in columns:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

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
        tutor_questions: int = 0,
    ) -> None:
        """Merge an event into a step's progress. Nothing is ever un-done."""
        with self._db() as db:
            db.execute(
                """
                INSERT INTO progress
                    (user_id, module_id, step_ref, done, attempts, hints_used,
                     showed_solution, tutor_questions, updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (user_id, module_id, step_ref) DO UPDATE SET
                    done = MAX(done, excluded.done),
                    attempts = attempts + excluded.attempts,
                    hints_used = MAX(hints_used, excluded.hints_used),
                    showed_solution = MAX(showed_solution, excluded.showed_solution),
                    tutor_questions = tutor_questions + excluded.tutor_questions,
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
                    tutor_questions,
                    time.time(),
                ),
            )

    def progress(self, user: User, module_id: str) -> dict[str, StepProgress]:
        with self._db() as db:
            rows = db.execute(
                "SELECT step_ref, done, attempts, hints_used, showed_solution, tutor_questions "
                "FROM progress "
                "WHERE user_id = ? AND module_id = ?",
                (user.id, module_id),
            ).fetchall()
        return {
            ref: StepProgress(bool(done), attempts, hints, bool(showed), tutor)
            for ref, done, attempts, hints, showed, tutor in rows
        }

    # --- projects --------------------------------------------------------------

    def project_level(self, user: User, module_id: str, lesson_slug: str) -> str:
        with self._db() as db:
            row = db.execute(
                "SELECT level FROM project_levels WHERE user_id = ? AND module_id = ? "
                "AND lesson_slug = ?",
                (user.id, module_id, lesson_slug),
            ).fetchone()
        return row[0] if row else "guided"

    def set_project_level(self, user: User, module_id: str, lesson_slug: str, level: str) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO project_levels (user_id, module_id, lesson_slug, level) "
                "VALUES (?, ?, ?, ?) ON CONFLICT (user_id, module_id, lesson_slug) "
                "DO UPDATE SET level = excluded.level",
                (user.id, module_id, lesson_slug, level),
            )

    def save_submission(self, user: User, exercise_id: str, code: str) -> None:
        """Keep the latest passing code per exercise (portfolio, carry-forward)."""
        with self._db() as db:
            db.execute(
                "INSERT INTO submissions (user_id, exercise_id, code, passed_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT (user_id, exercise_id) "
                "DO UPDATE SET code = excluded.code, passed_at = excluded.passed_at",
                (user.id, exercise_id, code, time.time()),
            )

    def submission(self, user: User, exercise_id: str) -> tuple[str, float] | None:
        with self._db() as db:
            row = db.execute(
                "SELECT code, passed_at FROM submissions WHERE user_id = ? AND exercise_id = ?",
                (user.id, exercise_id),
            ).fetchone()
        return (row[0], row[1]) if row else None

    # --- AI settings -----------------------------------------------------------

    def ai_settings(self, user: User) -> AISettingsRow:
        with self._db() as db:
            row = db.execute(
                "SELECT provider, model, api_key_encrypted FROM ai_settings WHERE user_id = ?",
                (user.id,),
            ).fetchone()
        if row is None:
            return AISettingsRow()
        key = None
        if row[2]:
            try:
                key = self._fernet.decrypt(row[2]).decode("utf-8")
            except InvalidToken:
                key = None  # the server secret changed; the learner re-enters the key
        return AISettingsRow(provider=row[0], model=row[1], api_key=key)

    def save_ai_settings(
        self,
        user: User,
        *,
        provider: str | None,
        model: str | None,
        api_key: str | None = None,
        clear_key: bool = False,
    ) -> None:
        """Save the choice; `api_key=None` keeps the stored key unless `clear_key`."""
        current = self.ai_settings(user)
        key = None if clear_key else (api_key if api_key is not None else current.api_key)
        encrypted = self._fernet.encrypt(key.encode("utf-8")) if key else None
        with self._db() as db:
            db.execute(
                """
                INSERT INTO ai_settings (user_id, provider, model, api_key_encrypted)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (user_id) DO UPDATE SET
                    provider = excluded.provider,
                    model = excluded.model,
                    api_key_encrypted = excluded.api_key_encrypted
                """,
                (user.id, provider, model, encrypted),
            )


def _load_secret(db_path: Path) -> bytes:
    """Key for encrypting API keys: DOJO_SECRET_KEY, else a key file next to the database."""
    if env := os.environ.get("DOJO_SECRET_KEY"):
        return env.encode("ascii")
    key_file = db_path.with_name("secret.key")
    if not key_file.exists():
        key_file.write_bytes(Fernet.generate_key())
        key_file.chmod(0o600)
    return key_file.read_bytes().strip()


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
