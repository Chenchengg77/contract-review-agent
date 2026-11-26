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
        # 轻量迁移：给 users 加偏好字段（已有库也能升级）
        cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
        if "default_contract_type" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN default_contract_type TEXT NOT NULL DEFAULT ''")
        if "default_focus" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN default_focus TEXT NOT NULL DEFAULT ''")
        if "perspective" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN perspective TEXT NOT NULL DEFAULT ''")
        # 轻量迁移：最近登录时间 + 账号状态（active / disabled）
        if "last_login" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN last_login REAL NOT NULL DEFAULT 0")
        if "user_status" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN user_status TEXT NOT NULL DEFAULT 'active'")
        # 轻量迁移：安全问题（用于自助找回密码）
        if "security_question" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN security_question TEXT NOT NULL DEFAULT ''")
        if "security_answer_hash" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN security_answer_hash TEXT NOT NULL DEFAULT ''")
        # 轻量迁移：reviews 存判定明细（供 AI 对话回答"哪条高风险"）
        rcols = [r[1] for r in c.execute("PRAGMA table_info(reviews)").fetchall()]
        if "judgments" not in rcols:
            c.execute("ALTER TABLE reviews ADD COLUMN judgments TEXT NOT NULL DEFAULT ''")
        if "status" not in rcols:
            c.execute("ALTER TABLE reviews ADD COLUMN status TEXT NOT NULL DEFAULT 'ok'")
        if "error" not in rcols:
            c.execute("ALTER TABLE reviews ADD COLUMN error TEXT NOT NULL DEFAULT ''")
        if "duration" not in rcols:
            c.execute("ALTER TABLE reviews ADD COLUMN duration REAL NOT NULL DEFAULT 0")
        # 运行时配置（管理员可改）
        c.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )


# ---- 审查偏好 ----
def get_preferences(user_id: int) -> dict:
    with _db() as c:
        row = c.execute(
            "SELECT default_contract_type, default_focus, perspective FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
    if not row:
        return {"default_contract_type": "", "default_focus": "", "perspective": ""}
    return dict(row)


def set_preferences(user_id: int, contract_type: str, focus: str, perspective: str = "") -> None:
    with _db() as c:
        c.execute(
            "UPDATE users SET default_contract_type=?, default_focus=?, perspective=? WHERE id=?",
            (contract_type or "", focus or "", perspective or "", user_id),
        )


# ---- 统计 ----
def contract_category(filename: str) -> str:
    """从文件名推合同类别：买卖_xxx.docx → 买卖。"""
    stem = (filename or "").rsplit(".", 1)[0]
    if "_" in stem:
        return stem.split("_", 1)[0]
    return "其他"


def _aggregate(reviews: list[dict]) -> dict:
    from collections import Counter

    cats = Counter(contract_category(r["filename"]) for r in reviews)
    return {
        "total": len(reviews),
        "high": sum(r["high"] for r in reviews),
        "mid": sum(r["mid"] for r in reviews),
        "low": sum(r["low"] for r in reviews),
        "by_category": [{"name": k, "count": v} for k, v in cats.most_common()],
    }


def user_stats(user_id: int) -> dict:
    with _db() as c:
        rows = c.execute(
            "SELECT filename, high, mid, low, created_at, judgments FROM reviews WHERE user_id=? "
            "ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    reviews = [dict(r) for r in rows]
    out = _aggregate(reviews)
    out["recent"] = reviews[:10]

    # 风险画像：按「合同类型」分组，统计各类型下最常出问题的条款
    import json

    def _load_js(r: dict) -> list[dict]:
        raw = r.get("judgments") or ""
        try:
            return json.loads(raw) if raw else []
        except Exception:  # noqa: BLE001
            return []

    by_type: dict[str, dict] = {}
    for r in reviews:
        cat = contract_category(r["filename"])
        t = by_type.setdefault(cat, {"type": cat, "reviews": 0, "counter": {}})
        t["reviews"] += 1
        for j in _load_js(r):
            clause = j.get("clause")
            if not clause:
                continue
            d = t["counter"].setdefault(clause, {"clause": clause, "high": 0, "mid": 0})
            sev = j.get("severity")
            if sev == "高":
                d["high"] += 1
            elif sev == "中":
                d["mid"] += 1

    profiles = []
    for t in by_type.values():
        tops = sorted(t["counter"].values(), key=lambda x: (-x["high"], -x["mid"]))[:3]
        profiles.append({"type": t["type"], "reviews": t["reviews"], "top_clauses": tops})
    profiles.sort(key=lambda x: -x["reviews"])
    out["type_profiles"] = profiles[:4]
    return out


def global_stats() -> dict:
    with _db() as c:
        user_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        rows = c.execute(
            "SELECT r.user_id, u.username, r.filename, r.high, r.mid, r.low, r.created_at "
            "FROM reviews r JOIN users u ON r.user_id=u.id"
        ).fetchall()
    reviews = [dict(r) for r in rows]
    out = _aggregate(reviews)
    out["users"] = user_count

    # 活跃用户 Top 5（按审查次数）
    from collections import Counter

    counts = Counter(r["username"] for r in reviews)
    out["top_users"] = [{"username": k, "count": v} for k, v in counts.most_common(5)]
    return out


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
def create_user(
    username: str,
    password: str,
    role: str = "user",
    question: str = "",
    answer: str = "",
) -> dict:
    username = username.strip()
    if len(username) < 2 or len(password) < 6:
        raise ValueError("用户名至少 2 位、密码至少 6 位")
    question = (question or "").strip()
    answer = (answer or "").strip()
    answer_hash = hash_password(answer.lower()) if question and answer else ""
    with _db() as c:
        try:
            cur = c.execute(
                "INSERT INTO users(username, password_hash, role, created_at, security_question, security_answer_hash) "
                "VALUES(?,?,?,?,?,?)",
                (
                    username,
                    hash_password(password),
                    role,
                    time.time(),
                    question if answer_hash else "",
                    answer_hash,
                ),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError("用户名已存在") from e
        uid = cur.lastrowid
    return {"id": uid, "username": username, "role": role}


def get_security_question(username: str) -> str | None:
    """返回该用户设置的安全问题；用户不存在或无问题返回 None。"""
    with _db() as c:
        row = c.execute(
            "SELECT security_question FROM users WHERE username=?", (username.strip(),)
        ).fetchone()
    return (row["security_question"] or "") if row else None


def verify_security_answer(username: str, answer: str) -> bool:
    with _db() as c:
        row = c.execute(
            "SELECT security_answer_hash FROM users WHERE username=?", (username.strip(),)
        ).fetchone()
    if not row or not row["security_answer_hash"]:
        return False
    return verify_password((answer or "").strip().lower(), row["security_answer_hash"])


def reset_password(username: str, new_password: str) -> bool:
    if len(new_password) < 6:
        raise ValueError("新密码至少 6 位")
    with _db() as c:
        row = c.execute("SELECT id FROM users WHERE username=?", (username.strip(),)).fetchone()
        if not row:
            return False
        c.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hash_password(new_password), row["id"]),
        )
        # 重置后清掉所有会话，强制重新登录
        c.execute("DELETE FROM sessions WHERE user_id=?", (row["id"],))
    return True


def set_security_question(user_id: int, question: str, answer: str) -> bool:
    """给已有账号补设安全问题（注册时没设置的老账号用）。"""
    question = (question or "").strip()
    answer = (answer or "").strip()
    if not question or not answer:
        raise ValueError("安全问题和答案都不能为空")
    with _db() as c:
        cur = c.execute(
            "UPDATE users SET security_question=?, security_answer_hash=? WHERE id=?",
            (question, hash_password(answer.lower()), user_id),
        )
        return cur.rowcount > 0


def authenticate(username: str, password: str) -> dict | None:
    with _db() as c:
        row = c.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        if (row["user_status"] or "active") == "disabled":
            raise PermissionError("账号已被禁用，请联系管理员")
        c.execute("UPDATE users SET last_login=? WHERE id=?", (time.time(), row["id"]))
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


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


# ---- 运行时配置 ----
def get_setting(key: str, default: str = "") -> str:
    with _db() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with _db() as c:
        c.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def health_stats() -> dict:
    """健康检查：DB、总量、失败数、成功率、平均耗时、最近一次时间。"""
    with _db() as c:
        db_ok = c.execute("SELECT 1").fetchone() is not None
        total = c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        failed = c.execute("SELECT COUNT(*) FROM reviews WHERE status='failed'").fetchone()[0]
        avg_dur = c.execute(
            "SELECT AVG(duration) FROM reviews WHERE status='ok' AND duration>0"
        ).fetchone()[0]
        last = c.execute("SELECT created_at FROM reviews ORDER BY created_at DESC LIMIT 1").fetchone()
    return {
        "db": db_ok,
        "total": total,
        "failed": failed,
        "success_rate": round((total - failed) / total, 4) if total else 1.0,
        "avg_duration": round(float(avg_dur or 0), 1),
        "last_at": last["created_at"] if last else None,
    }


def recent_failures(limit: int = 20) -> list[dict]:
    with _db() as c:
        rows = c.execute(
            "SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id=u.id "
            "WHERE r.status='failed' ORDER BY r.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_review(review_id: int) -> dict | None:
    with _db() as c:
        row = c.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
    return dict(row) if row else None


def mark_retried(review_id: int) -> None:
    """重试成功后，把原失败记录标记为已处理（不再计入失败率）。"""
    with _db() as c:
        c.execute("UPDATE reviews SET status='retried' WHERE id=?", (review_id,))


def clear_failures(demo_only: bool = True) -> int:
    """把失败记录标记为已处理。

    demo_only=True 时只清理 [DEMO] 开头的演示数据，**真实失败记录保留**，避免掩盖事故。
    """
    with _db() as c:
        if demo_only:
            cur = c.execute(
                "UPDATE reviews SET status='retried' WHERE status='failed' AND error LIKE ?",
                ("[DEMO]%",),
            )
        else:
            cur = c.execute("UPDATE reviews SET status='retried' WHERE status='failed'")
        return cur.rowcount


# ---- 审查记录 ----
def add_review(
    user_id: int,
    filename: str,
    high: int,
    mid: int,
    low: int,
    judgments: list[dict] | None = None,
    status: str = "ok",
    error: str = "",
    duration: float = 0,
    created_at: float | None = None,
) -> None:
    import json

    payload = json.dumps(judgments, ensure_ascii=False) if judgments else ""
    with _db() as c:
        c.execute(
            "INSERT INTO reviews(user_id, filename, high, mid, low, created_at, judgments, status, error, duration) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                user_id,
                filename,
                high,
                mid,
                low,
                created_at if created_at is not None else time.time(),
                payload,
                status,
                error,
                duration,
            ),
        )


def latest_review(filename: str) -> dict | None:
    """取某份合同最近一次审查（含判定明细），供 AI 对话回答"哪条高风险"。"""
    import json

    with _db() as c:
        row = c.execute(
            "SELECT * FROM reviews WHERE filename=? ORDER BY created_at DESC LIMIT 1",
            (filename,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    raw = d.pop("judgments", "") or ""
    try:
        d["judgments"] = json.loads(raw) if raw else []
    except Exception:  # noqa: BLE001
        d["judgments"] = []
    return d


def list_reviews(user_id: int | None = None, limit: int | None = None) -> list[dict]:
    """user_id=None 表示查全部（管理员）；limit=None 表示不限条数。"""
    with _db() as c:
        sql = (
            "SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id=u.id "
            + ("WHERE r.user_id=? " if user_id is not None else "")
            + "ORDER BY r.created_at DESC"
        )
        params: list = [] if user_id is None else [user_id]
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def list_users() -> list[dict]:
    with _db() as c:
        rows = c.execute(
            """SELECT u.id, u.username, u.role, u.created_at,
                      u.default_contract_type, u.default_focus, u.perspective,
                      u.last_login, u.user_status,
                      (SELECT COUNT(*) FROM reviews r WHERE r.user_id = u.id) AS review_count
               FROM users u ORDER BY u.id"""
        ).fetchall()
    return [dict(r) for r in rows]


def set_user_status(user_id: int, status: str) -> bool:
    """启用 / 禁用账号。禁用后该用户的会话立即失效。"""
    if status not in ("active", "disabled"):
        raise ValueError("状态只能是 active 或 disabled")
    with _db() as c:
        cur = c.execute("UPDATE users SET user_status=? WHERE id=?", (status, user_id))
        if cur.rowcount and status == "disabled":
            c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        return cur.rowcount > 0


def update_user(user_id: int, role: str | None = None, password: str | None = None) -> bool:
    """修改角色 / 重置密码。"""
    with _db() as c:
        exists = c.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone()
        if not exists:
            return False
        if role:
            if role not in ("user", "admin"):
                raise ValueError("角色不合法")
            c.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        if password:
            if len(password) < 6:
                raise ValueError("密码至少 6 位")
            c.execute(
                "UPDATE users SET password_hash=? WHERE id=?",
                (hash_password(password), user_id),
            )
        return True


def delete_user(user_id: int) -> bool:
    """删除用户，并级联删除其会话和审查记录。"""
    with _db() as c:
        c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM reviews WHERE user_id=?", (user_id,))
        cur = c.execute("DELETE FROM users WHERE id=?", (user_id,))
        return cur.rowcount > 0


def delete_review(review_id: int) -> bool:
    with _db() as c:
        cur = c.execute("DELETE FROM reviews WHERE id=?", (review_id,))
        return cur.rowcount > 0
