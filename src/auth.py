"""用户账号系统：注册、登录、会话、权限（SQLite 存储，零额外依赖）。

设计：
- 密码用 PBKDF2-SHA256 + 随机盐哈希，绝不存明文。
- 登录后发放随机 token（7 天有效），前端用 Authorization: Bearer <token> 携带。
- 角色：user / admin（admin 可看全部用户与记录）。
- 数据库：data/app.db（sqlite），首次调用自动建表。
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """建表（幂等）。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at REAL NOT NULL
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at REAL NOT NULL
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                high INTEGER NOT NULL DEFAULT 0,
                mid INTEGER NOT NULL DEFAULT 0,
                low INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            )"""
        )


# ---- 密码 ----
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        return secrets.compare_digest(digest.hex(), hash_hex)
    except Exception:  # noqa: BLE001
        return False


# ---- 用户 ----
def create_user(username: str, password: str, role: str = "user") -> dict:
    username = username.strip()
    if len(username) < 2 or len(password) < 6:
        raise ValueError("用户名至少 2 位、密码至少 6 位")
    with _db() as c:
        try:
            cur = c.execute(
                "INSERT INTO users(username, password_hash, role, created_at) VALUES(?,?,?,?)",
                (username, hash_password(password), role, time.time()),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError("用户名已存在") from e
        uid = cur.lastrowid
    return {"id": uid, "username": username, "role": role}


def authenticate(username: str, password: str) -> dict | None:
    with _db() as c:
        row = c.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
    if row and verify_password(password, row["password_hash"]):
        return {"id": row["id"], "username": row["username"], "role": row["role"]}
    return None


# ---- 会话 ----
def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with _db() as c:
        c.execute(
            "INSERT INTO sessions(token, user_id, expires_at) VALUES(?,?,?)",
            (token, user_id, time.time() + 7 * 86400),
        )
    return token


def get_user_by_token(token: str) -> dict | None:
    with _db() as c:
        row = c.execute(
            """SELECT u.id, u.username, u.role FROM sessions s
               JOIN users u ON s.user_id = u.id
               WHERE s.token=? AND s.expires_at > ?""",
            (token, time.time()),
        ).fetchone()
    return dict(row) if row else None


def delete_session(token: str) -> None:
    with _db() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))


# ---- 审查记录 ----
def add_review(user_id: int, filename: str, high: int, mid: int, low: int) -> None:
    with _db() as c:
        c.execute(
            "INSERT INTO reviews(user_id, filename, high, mid, low, created_at) VALUES(?,?,?,?,?,?)",
            (user_id, filename, high, mid, low, time.time()),
        )


def list_reviews(user_id: int | None = None, limit: int = 50) -> list[dict]:
    """user_id=None 表示查全部（管理员）。"""
    with _db() as c:
        if user_id is None:
            rows = c.execute(
                "SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id=u.id "
                "ORDER BY r.created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id=u.id "
                "WHERE r.user_id=? ORDER BY r.created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def list_users() -> list[dict]:
    with _db() as c:
        rows = c.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]
