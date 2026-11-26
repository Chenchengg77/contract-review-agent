"""FastAPI 后端：把审查流水线暴露成 HTTP API，并托管前端静态文件。

运行：uvicorn api:app --reload
前端：static/ 目录（index.html + app.js）
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import config
from src.parser import parse, clause_headings, parse_blocks
from src import extract as EX
from src import qa
from src import law_qa
from src import revision
from src import auth
from src import workflow as WF
from src.assess import assess, _find_clause_text

app = FastAPI(title="合同智能审查 API")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# 初始化用户库，并确保有一个默认管理员（admin / admin123，生产请改）
auth.init_db()
try:
    if not any(u["role"] == "admin" for u in auth.list_users()):
        auth.create_user("admin", "admin123", role="admin")
except Exception:  # noqa: BLE001
    pass
# 确保演示账号存在（登录页「一键体验 Demo」用；线上空库也能直接体验）
try:
    if not any(u["username"] == "demo" for u in auth.list_users()):
        auth.create_user("demo", "demo123456", role="user")
except Exception:  # noqa: BLE001
    pass


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """从 Authorization: Bearer <token> 解析当前用户。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    user = auth.get_user_by_token(authorization[7:])
    if not user:
        raise HTTPException(401, "登录已过期，请重新登录")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


# ---- 认证 ----
@app.post("/api/auth/register")
def register(payload: dict) -> dict:
    try:
        user = auth.create_user(
            payload.get("username", ""),
            payload.get("password", ""),
            question=payload.get("security_question", ""),
            answer=payload.get("security_answer", ""),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    token = auth.create_session(user["id"])
    return {"token": token, "user": user}


# ---- 找回密码（安全问题）----
_reset_attempts: dict[str, dict] = {}
RESET_MAX_TRIES = 5
RESET_LOCK_SECONDS = 600


@app.post("/api/auth/forgot/question")
def forgot_question(payload: dict) -> dict:
    """第一步：用用户名取回安全问题。"""
    username = str(payload.get("username", "")).strip()
    if not username:
        raise HTTPException(400, "请输入用户名")
    q = auth.get_security_question(username)
    if q is None:
        raise HTTPException(404, "用户不存在")
    if not q:
        raise HTTPException(400, "该账号未设置安全问题，请联系管理员重置密码")
    return {"username": username, "question": q}


@app.post("/api/auth/forgot/reset")
def forgot_reset(payload: dict) -> dict:
    """第二步：校验安全答案并重置密码（带失败限次）。"""
    username = str(payload.get("username", "")).strip()
    answer = str(payload.get("answer", "")).strip()
    new_password = str(payload.get("new_password", ""))
    if not username or not answer:
        raise HTTPException(400, "请填写用户名和答案")
    if len(new_password) < 6:
        raise HTTPException(400, "新密码至少 6 位")

    # 简单限次：同一用户名 10 分钟内最多试 5 次
    now = time.time()
    rec = _reset_attempts.get(username, {"n": 0, "until": 0})
    if rec["until"] > now:
        raise HTTPException(429, "尝试次数过多，请 10 分钟后再试")

    if not auth.verify_security_answer(username, answer):
        rec["n"] += 1
        if rec["n"] >= RESET_MAX_TRIES:
            rec = {"n": 0, "until": now + RESET_LOCK_SECONDS}
        _reset_attempts[username] = rec
        raise HTTPException(400, "答案不正确")

    _reset_attempts.pop(username, None)
    try:
        auth.reset_password(username, new_password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"message": "密码已重置，请用新密码登录"}


@app.post("/api/auth/login")
def login(payload: dict) -> dict:
    try:
        user = auth.authenticate(payload.get("username", ""), payload.get("password", ""))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if not user:
        raise HTTPException(401, "用户名或密码错误")
    token = auth.create_session(user["id"])
    return {"token": token, "user": user}


@app.post("/api/auth/change-password")
def change_password(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    """修改自己的密码：需校验旧密码。"""
    old = str(payload.get("old_password", ""))
    new = str(payload.get("new_password", ""))
    if len(new) < 6:
        raise HTTPException(400, "新密码至少 6 位")
    if new == old:
        raise HTTPException(400, "新密码不能与旧密码相同")
    if not auth.authenticate(user["username"], old):
        raise HTTPException(400, "旧密码不正确")
    auth.update_user(user["id"], password=new)
    return {"message": "密码已修改"}


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)) -> dict:
    if authorization and authorization.startswith("Bearer "):
        auth.delete_session(authorization[7:])
    return {"message": "已退出"}


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    out = dict(user)
    try:
        out["has_security_question"] = bool(auth.get_security_question(out["username"]))
    except Exception:  # noqa: BLE001
        out["has_security_question"] = False
    return out


@app.post("/api/auth/security-question")
def set_security_question(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    """已登录用户设置/修改安全问题（用于将来找回密码）。"""
    try:
        auth.set_security_question(
            user["id"], payload.get("question", ""), payload.get("answer", "")
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"message": "安全问题已保存"}


@app.get("/api/me/preferences")
def get_preferences(user: dict = Depends(get_current_user)) -> dict:
    return auth.get_preferences(user["id"])


@app.put("/api/me/preferences")
def put_preferences(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    auth.set_preferences(
        user["id"],
        payload.get("default_contract_type", ""),
        payload.get("default_focus", ""),
        payload.get("perspective", ""),
    )
    return auth.get_preferences(user["id"])


@app.get("/api/me/stats")
def my_stats(user: dict = Depends(get_current_user)) -> dict:
    """当前用户的审查统计。"""
    return auth.user_stats(user["id"])


@app.get("/api/admin/stats")
def admin_stats(user: dict = Depends(require_admin)) -> dict:
    """全局聚合统计（不暴露个人合同明细）。"""
    return auth.global_stats()


@app.get("/api/admin/health")
def admin_health(user: dict = Depends(require_admin)) -> dict:
    """系统健康检查：DB、成功/失败、平均耗时、最近一次时间、依赖服务。"""
    h = auth.health_stats()
    # 文件解析服务：样例目录可读
    try:
        files_ok = config.RAW_DIR.exists() and config.RAW_DIR.is_dir()
    except Exception:  # noqa: BLE001
        files_ok = False
    h["services"] = {
        "db": bool(h.get("db")),
        # AI 服务：有 Key 即视为已配置（不做联网探测，避免每次刷新打外部接口）
        "llm": bool(config.DEEPSEEK_API_KEY),
        "files": files_ok,
    }
    return h


@app.get("/api/admin/failures")
def admin_failures(user: dict = Depends(require_admin)) -> dict:
    """最近失败的审查记录。"""
    return {"failures": auth.recent_failures(20)}


@app.post("/api/admin/retry/{review_id}")
def admin_retry(review_id: int, user: dict = Depends(require_admin)) -> dict:
    """重试一条失败的审查（仅示例库中的合同；上传文件已删除的需用户重传）。"""
    r = auth.get_review(review_id)
    if not r:
        raise HTTPException(404, "记录不存在")
    name = r["filename"]
    path = (config.RAW_DIR / name).resolve()
    if not str(path).startswith(str(config.RAW_DIR.resolve())) or not path.exists():
        raise HTTPException(400, "原始文件不在示例库中（上传文件已删除），请让用户重新上传")

    t0 = time.time()
    try:
        result = _run_review(path)
    except Exception as e:  # noqa: BLE001
        auth.add_review(user["id"], name, 0, 0, 0, None, status="failed", error=str(e)[:300])
        raise HTTPException(500, f"重试仍失败：{str(e)[:80]}") from e
    dt = time.time() - t0
    ov = result["overview"]
    auth.add_review(
        user["id"], name, ov["high"], ov["mid"], ov["low"], result.get("judgments"), duration=round(dt, 1)
    )
    auth.mark_retried(review_id)
    return {"ok": True, "overview": ov}


@app.post("/api/admin/settings/reset")
def admin_reset_settings(user: dict = Depends(require_admin)) -> dict:
    """恢复默认配置。"""
    auth.set_setting("guard_on", "1")
    auth.set_setting("guard_low", "5.0")
    auth.set_setting("guard_high", "8.0")
    return {
        "guard_on": auth.get_setting("guard_on", "1") == "1",
        "guard_low": float(auth.get_setting("guard_low", "5.0") or 5.0),
        "guard_high": float(auth.get_setting("guard_high", "8.0") or 8.0),
    }


@app.post("/api/admin/failures/clear")
def admin_clear_failures(user: dict = Depends(require_admin)) -> dict:
    """只清理演示数据（[DEMO] 开头）的失败记录；真实故障记录保留。"""
    return {"ok": True, "cleared": auth.clear_failures(demo_only=True)}


@app.post("/api/admin/demo/failure")
def admin_demo_failure(user: dict = Depends(require_admin)) -> dict:
    """演示用：注入足够多的模拟失败，使失败率超过 5% 阈值（错误信息带 [DEMO] 标记）。"""
    errors = [
        "[DEMO] ReadTimeout: DeepSeek API timeout after 180s",
        "[DEMO] HTTPError 429: Too Many Requests（限流）",
        "[DEMO] ConnectionError: 网络连接中断",
        "[DEMO] TimeoutError: 解析超时（>60s）",
        "[DEMO] HTTPError 500: 上游服务异常",
    ]
    # 合同、用户、时间都做分散，避免注入出一堆一模一样的记录
    try:
        files = [p.name for p in sorted(config.RAW_DIR.glob("*.docx"))][:10]
    except Exception:  # noqa: BLE001
        files = []
    if not files:
        files = ["示例合同.docx"]
    others = [u for u in auth.list_users() if u["role"] != "admin"]
    targets = others or [user]

    h = auth.health_stats()
    total = h["total"] or 1
    need = max(6, int(total * 0.06) + 1 - h["failed"])
    now = time.time()
    for i in range(need):
        uid = targets[i % len(targets)]["id"]
        fname = files[i % len(files)]
        # 分散在最近 3 小时内（每条错开 7~25 分钟）
        ts = now - (i % 12) * 780 - (i * 137 % 420)
        auth.add_review(
            uid,
            fname,
            0,
            0,
            0,
            None,
            status="failed",
            error=errors[i % len(errors)],
            created_at=ts,
        )
    h2 = auth.health_stats()
    return {
        "ok": True,
        "injected": need,
        "failed": h2["failed"],
        "total": h2["total"],
        "rate": round(h2["failed"] / (h2["total"] or 1), 4),
    }


@app.get("/api/admin/settings")
def admin_get_settings(user: dict = Depends(require_admin)) -> dict:
    """运行时配置（AI 拦截开关与阈值、审查超时）。"""
    return {
        "guard_on": auth.get_setting("guard_on", "1") == "1",
        "guard_low": float(auth.get_setting("guard_low", "5.0") or 5.0),
        "guard_high": float(auth.get_setting("guard_high", "8.0") or 8.0),
        "review_timeout": float(auth.get_setting("review_timeout", "180") or 180),
    }


@app.put("/api/admin/settings")
def admin_put_settings(payload: dict, user: dict = Depends(require_admin)) -> dict:
    """更新运行时配置。"""
    if "guard_on" in payload:
        auth.set_setting("guard_on", "1" if payload["guard_on"] else "0")
    if "guard_low" in payload:
        auth.set_setting("guard_low", str(payload["guard_low"]))
    if "guard_high" in payload:
        auth.set_setting("guard_high", str(payload["guard_high"]))
    if "review_timeout" in payload:
        auth.set_setting("review_timeout", str(payload["review_timeout"]))
    return {
        "guard_on": auth.get_setting("guard_on", "1") == "1",
        "guard_low": float(auth.get_setting("guard_low", "5.0") or 5.0),
        "guard_high": float(auth.get_setting("guard_high", "8.0") or 8.0),
        "review_timeout": float(auth.get_setting("review_timeout", "180") or 180),
    }


@app.get("/api/reviews")
def my_reviews(user: dict = Depends(get_current_user)) -> dict:
    """当前用户的审查记录；管理员看全部。"""
    rows = auth.list_reviews(None if user["role"] == "admin" else user["id"])
    for r in rows:
        r["category"] = auth.contract_category(r.get("filename", ""))
    return {"reviews": rows}


@app.get("/api/reviews/{review_id}")
def review_detail(review_id: int, user: dict = Depends(get_current_user)) -> dict:
    """单条审查记录详情（含判定明细），本人或管理员可看。"""
    r = auth.get_review(review_id)
    if not r:
        raise HTTPException(404, "记录不存在")
    if user["role"] != "admin" and r.get("user_id") != user["id"]:
        raise HTTPException(403, "无权查看该记录")
    r["category"] = auth.contract_category(r.get("filename", ""))
    try:
        r["judgments"] = json.loads(r.get("judgments") or "[]")
    except Exception:  # noqa: BLE001
        r["judgments"] = []
    return r


@app.get("/api/contract_text")
def contract_text(name: str, user: dict = Depends(get_current_user)) -> dict:
    """读取合同原文（解析后文本），用于管理端查看原合同。"""
    safe = Path(name).name
    path = config.RAW_DIR / safe
    if not path.exists():
        raise HTTPException(404, "合同文件不存在")
    try:
        paras = parse(str(path))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"解析失败：{e}")
    text = "\n".join(str(p.get("text", "")) for p in paras if p.get("text"))
    return {"name": safe, "text": text[:30000], "truncated": len(text) > 30000}


@app.get("/api/admin/users")
def admin_users(user: dict = Depends(require_admin)) -> dict:
    return {"users": auth.list_users()}


@app.post("/api/admin/users")
def admin_create_user(payload: dict, user: dict = Depends(require_admin)) -> dict:
    """管理员新建账号。"""
    role = payload.get("role", "user")
    if role not in ("user", "admin"):
        raise HTTPException(400, "角色不合法")
    try:
        created = auth.create_user(payload.get("username", ""), payload.get("password", ""), role)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"message": "已创建", "user": created}


@app.patch("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, payload: dict, user: dict = Depends(require_admin)) -> dict:
    """编辑用户：改角色 / 重置密码。"""
    users = auth.list_users()
    target = next((u for u in users if u["id"] == user_id), None)
    if not target:
        raise HTTPException(404, "用户不存在")
    role = payload.get("role")
    if role == "user" and target["role"] == "admin":
        active_admins = sum(1 for u in users if u["role"] == "admin" and u["user_status"] == "active")
        if active_admins <= 1:
            raise HTTPException(400, "不能降级最后一个管理员")
    try:
        auth.update_user(user_id, role=role, password=payload.get("password") or None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"message": "已更新"}


@app.patch("/api/admin/users/{user_id}/status")
def admin_set_user_status(user_id: int, payload: dict, user: dict = Depends(require_admin)) -> dict:
    """启用 / 禁用账号。"""
    status = payload.get("status", "")
    if status not in ("active", "disabled"):
        raise HTTPException(400, "状态不合法")
    if user_id == user["id"] and status == "disabled":
        raise HTTPException(400, "不能禁用自己的账号")
    users = auth.list_users()
    target = next((u for u in users if u["id"] == user_id), None)
    if not target:
        raise HTTPException(404, "用户不存在")
    if target["role"] == "admin" and status == "disabled":
        if sum(1 for u in users if u["role"] == "admin" and u["user_status"] == "active") <= 1:
            raise HTTPException(400, "不能禁用最后一个管理员")
    auth.set_user_status(user_id, status)
    return {"message": "已更新"}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, user: dict = Depends(require_admin)) -> dict:
    """删除用户（级联删除其会话与审查记录）。"""
    if user_id == user["id"]:
        raise HTTPException(400, "不能删除自己")
    users = auth.list_users()
    target = next((u for u in users if u["id"] == user_id), None)
    if not target:
        raise HTTPException(404, "用户不存在")
    if target["role"] == "admin" and sum(1 for u in users if u["role"] == "admin") <= 1:
        raise HTTPException(400, "不能删除最后一个管理员")
    auth.delete_user(user_id)
    return {"message": "已删除"}


@app.delete("/api/reviews/{review_id}")
def admin_delete_review(review_id: int, user: dict = Depends(require_admin)) -> dict:
    """删除一条审查记录（管理员）。"""
    if not auth.delete_review(review_id):
        raise HTTPException(404, "记录不存在")
    return {"message": "已删除"}

# 惰性单例
_client = None
_client_timeout = None
_types = None


def _get_client():
    """按管理员配置的「审查超时」创建客户端；超时值变化时自动重建。"""
    global _client, _client_timeout
    try:
        timeout = float(auth.get_setting("review_timeout", "180") or 180)
    except ValueError:
        timeout = 180.0
    if _client is None or _client_timeout != timeout:
        _client = EX.make_client(timeout=timeout)
        _client_timeout = timeout
    return _client


def _get_types():
    global _types
    if _types is None:
        _types = EX.load_clause_types()
    return _types


def _run_review(path: Path, focus: str = "", perspective: str = "") -> dict:
    """执行完整审查流水线，返回结构化结果。focus 关注点，perspective 审查立场。"""
    t0 = time.time()
    paragraphs = parse(path)
    clauses, usage = EX.extract(_get_client(), paragraphs, _get_types())
    clauses = EX.validate(paragraphs, clauses)
    judgments = assess(clauses, _get_types(), paragraphs, _get_client(), perspective)

    # 对偏离/冲突条款生成修订建议
    clause_map = {c["type"]: c for c in clauses}
    playbook = {t["name"]: t for t in _get_types()}
    for j in judgments:
        if j.get("present") and j.get("verdict") in ("偏离", "冲突"):
            c = clause_map.get(j["clause"])
            full = (
                _find_clause_text(paragraphs, c.get("clause_no"), c.get("evidence"))
                if c else ""
            )
            try:
                j["revision"] = revision.generate_revision(
                    j["clause"], full or j.get("evidence", ""), playbook[j["clause"]], _get_client(), focus, perspective
                )
            except Exception:  # noqa: BLE001
                j["revision"] = ""

    dt = time.time() - t0

    heads = clause_headings(paragraphs)
    high = [j for j in judgments if j["severity"] == "高"]
    mid = [j for j in judgments if j["severity"] == "中"]
    low = [j for j in judgments if j["severity"] == "低"]

    return {
        "process": {
            "paragraphs": len(paragraphs),
            "headings": len(heads),
            "seconds": round(dt, 1),
            "tokens": usage["total_tokens"],
        },
        "overview": {"high": len(high), "mid": len(mid), "low": len(low)},
        "judgments": judgments,
    }


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _extract_clauses(path: Path) -> dict:
    """抽取 13 类条款，返回 {type: {present, evidence, text}}。"""
    paragraphs = parse(path)
    clauses, _ = EX.extract(_get_client(), paragraphs, _get_types())
    clauses = EX.validate(paragraphs, clauses)
    out = {}
    for c in clauses:
        text = (
            _find_clause_text(paragraphs, c.get("clause_no"), c.get("evidence"))
            if c.get("present")
            else ""
        )
        out[c["type"]] = {
            "present": bool(c.get("present")),
            "evidence": c.get("evidence", ""),
            "text": text,
        }
    return out


def _compare(a: dict, b: dict) -> dict:
    """逐条比对 13 类条款，输出变化类型。"""
    summary = {"修改": 0, "新增": 0, "删除": 0, "相同": 0}
    diffs = []
    for typ in a:
        ca, cb = a[typ], b[typ]
        if ca["present"] and cb["present"]:
            change = "修改" if _norm(ca["text"]) != _norm(cb["text"]) else "相同"
        elif ca["present"] and not cb["present"]:
            change = "删除"
        elif not ca["present"] and cb["present"]:
            change = "新增"
        else:
            change = "相同"
        summary[change] += 1
        diffs.append({
            "clause": typ,
            "change": change,
            "a_text": ca["text"] or "（无此类条款）",
            "b_text": cb["text"] or "（无此类条款）",
        })
    return {"summary": summary, "diffs": diffs}


# 变化类型 → 风险等级（没有审查数据时的规则兜底）
_CHANGE_SEVERITY = {"删除": "高", "修改": "中", "新增": "低"}
_CHANGE_NOTE = {
    "删除": "该条款在新版中消失，需确认是否为无意遗漏",
    "新增": "新版新增该条款，需确认义务与责任是否可接受",
    "修改": "条款正文有改动，需核对金额、期限、责任等关键要素",
}


def _enrich_diffs(result: dict, b_name: str) -> dict:
    """给差异补风险等级与简述：优先用 B 合同最近一次审查的判定，退化时按规则推断。"""
    sev_map: dict[str, str] = {}
    try:
        latest = auth.latest_review(b_name)
        for j in (latest or {}).get("judgments", []):
            if j.get("clause") and j.get("severity"):
                sev_map[j["clause"]] = j["severity"]
    except Exception:  # noqa: BLE001
        sev_map = {}

    for d in result.get("diffs", []):
        if d["change"] == "相同":
            d["severity"] = ""
            d["note"] = ""
            d["severity_from"] = ""
            continue
        sev = sev_map.get(d["clause"])
        d["severity_from"] = "review" if sev else "rule"
        d["severity"] = sev or _CHANGE_SEVERITY.get(d["change"], "中")
        d["note"] = _CHANGE_NOTE.get(d["change"], "")
    return result


@app.get("/api/contracts")
def list_contracts() -> dict:
    """返回示例合同列表。"""
    names = sorted(
        f.name for f in config.RAW_DIR.glob("*.docx") if not f.name.startswith("~$")
    )
    return {"contracts": names}


_TEMPLATE_DESCRIPTIONS = {
    "买卖": "适用于商品买卖交易，覆盖价款、交付、质量与违约责任。",
    "租赁": "适用于房屋 / 场地租赁，覆盖租金、押金、维修与转租。",
    "承揽": "适用于承揽 / 加工 / 定作，覆盖技术标准、验收与质保。",
    "服务": "适用于委托服务，覆盖服务内容、费用与保密。",
    "建设": "适用于建设工程 / 装修，覆盖工期、验收与质保。",
    "其他": "适用于运输、广告、旅游等场景的标准合同范本。",
    "示例": "填充示例（合规 / 冲突样本），用于演示审查与对比。",
}


def _clean_title(name: str) -> str:
    """把文件名清洗成展示标题：去掉 分类_ 前缀和 .docx 后缀。"""
    stem = name[:-5] if name.lower().endswith(".docx") else name
    if "_" in stem:
        stem = stem.split("_", 1)[1]
    return stem


_templates_cache = None


@app.get("/api/templates")
def list_templates(response: Response) -> dict:
    """返回合同模板库：分类 + 展示标题 + 描述 + 条款标题（带缓存）。"""
    response.headers["Cache-Control"] = "no-store"
    global _templates_cache
    if _templates_cache is None:
        result = []
        names = sorted(
            f.name for f in config.RAW_DIR.glob("*.docx") if not f.name.startswith("~$")
        )
        for name in names:
            category = name.split("_")[0] if "_" in name else "其他"
            try:
                paragraphs = parse(config.RAW_DIR / name)
                heads = clause_headings(paragraphs)
            except Exception:  # noqa: BLE001
                heads = []
            result.append({
                "name": name,
                "title": _clean_title(name),
                "category": category,
                "clause_count": len(heads),
                "description": _TEMPLATE_DESCRIPTIONS.get(category, "标准合同范本。"),
                "headings": [f"{h['clause_no']} {h['heading']}"[:50] for h in heads],
            })
        _templates_cache = result
    return {"templates": _templates_cache}


@app.get("/api/templates/download")
def download_template(name: str) -> FileResponse:
    """下载模板 .docx 文件。"""
    path = (config.RAW_DIR / name).resolve()
    if not str(path).startswith(str(config.RAW_DIR.resolve())) or not path.exists():
        raise HTTPException(404, "模板不存在")
    return FileResponse(
        path,
        filename=name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/api/templates/preview")
def template_preview(name: str) -> dict:
    """返回模板的完整内容（段落 + 表格，保留表格行列结构）。"""
    path = (config.RAW_DIR / name).resolve()
    if not str(path).startswith(str(config.RAW_DIR.resolve())) or not path.exists():
        raise HTTPException(404, "模板不存在")
    return {
        "name": name,
        "title": _clean_title(name),
        "blocks": parse_blocks(path),
    }


@app.post("/api/templates/upload")
async def upload_template(file: UploadFile = File(...), user: dict = Depends(get_current_user)) -> dict:
    """上传自定义模板（.docx），存入 data/raw（分类=自定义），清缓存。"""
    global _templates_cache
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "只支持 .docx 文件")

    base = re.sub(r'[\\/:*?"<>|]', "_", file.filename)
    dest = config.RAW_DIR / f"自定义_{base}"
    n = 1
    while dest.exists():
        dest = config.RAW_DIR / f"自定义_{Path(base).stem}_{n}.docx"
        n += 1

    content = await file.read()
    dest.write_bytes(content)
    _templates_cache = None
    return {"name": dest.name, "message": "上传成功"}


@app.get("/api/eval")
def eval_metrics() -> dict:
    """返回评估指标摘要 + 逐份合同结果 + 修复前后对比。"""
    p = config.RESULTS_DIR / "eval_v3.json"
    if not p.exists():
        return {"summary": None, "per_contract": []}
    data = json.loads(p.read_text(encoding="utf-8"))

    before = None
    before_p = config.RESULTS_DIR / "eval_v3_before_fix.json"
    if before_p.exists():
        before = json.loads(before_p.read_text(encoding="utf-8")).get("summary")

    cases: list = []
    cases_p = config.RESULTS_DIR / "compare_cases.json"
    if cases_p.exists():
        cases = json.loads(cases_p.read_text(encoding="utf-8")).get("cases", [])

    qa_cases: list = []
    qa_p = config.RESULTS_DIR / "compare_qa.json"
    if qa_p.exists():
        qa_cases = json.loads(qa_p.read_text(encoding="utf-8")).get("cases", [])

    return {
        "summary": data.get("summary", {}),
        "before": before,
        "cases": cases,
        "qa_cases": qa_cases,
        "per_contract": data.get("per_contract", []),
    }


# ===== LangGraph 编排：审查 + 人工确认（human-in-the-loop）=====
_graph_app = None
_graph_lock = threading.Lock()


def _get_graph():
    """全局单例编译图（MemorySaver 按 thread_id 保存状态）。"""
    global _graph_app
    with _graph_lock:
        if _graph_app is None:
            _graph_app = WF.new_app()
        return _graph_app


def _summarize(judgments: list[dict]) -> dict:
    return {
        "high": sum(1 for j in judgments if j.get("severity") == "高"),
        "mid": sum(1 for j in judgments if j.get("severity") == "中"),
        "low": sum(1 for j in judgments if j.get("severity") == "低"),
    }


def _pending_payload(app, cfg) -> dict | None:
    """图若停在 interrupt，取回暂停时给人工的信息。"""
    snap = app.get_state(cfg)
    if not snap.next:
        return None
    for task in getattr(snap, "tasks", None) or ():
        for it in getattr(task, "interrupts", None) or ():
            return it.value or {}
    return {}


def _graph_result(values: dict, tid: str, elapsed: float) -> dict:
    judgments = values.get("judgments", []) or []
    return {
        "status": "done",
        "thread_id": tid,
        "filename": values.get("filename", ""),
        "judgments": judgments,
        "clauses": values.get("clauses", []),
        "paragraphs": values.get("paragraphs", []),
        "report": values.get("report", ""),
        "overview": _summarize(judgments),
        "usage": values.get("usage", {}),
        "elapsed": elapsed,
    }


@app.post("/api/review_graph")
def review_graph(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    """用 LangGraph 跑审查：无高风险直接出报告；有高风险则暂停，返回 pending 等确认。"""
    name = str(payload.get("name", ""))
    path = (config.RAW_DIR / name).resolve()
    if not str(path).startswith(str(config.RAW_DIR.resolve())) or not path.exists():
        raise HTTPException(404, "合同不存在")

    graph = _get_graph()
    tid = f"rg-{user['id']}-{uuid.uuid4().hex[:8]}"
    cfg = {"configurable": {"thread_id": tid}}
    t0 = time.time()
    try:
        graph.invoke({"filename": name}, cfg)
    except Exception as e:  # noqa: BLE001
        auth.add_review(user["id"], name, 0, 0, 0, None, status="failed", error=str(e)[:300])
        raise HTTPException(500, f"审查失败：{e}") from e

    pending = _pending_payload(graph, cfg)
    if pending is not None:
        snap = graph.get_state(cfg)
        judgments = snap.values.get("judgments", []) or []
        return {
            "status": "pending",
            "thread_id": tid,
            "filename": name,
            "high_risk": pending.get("high_risk", []),
            "message": pending.get("message", ""),
            "judgments": judgments,
            "overview": _summarize(judgments),
            "elapsed": round(time.time() - t0, 1),
        }

    snap = graph.get_state(cfg)
    result = _graph_result(snap.values, tid, round(time.time() - t0, 1))
    ov = result["overview"]
    auth.add_review(
        user["id"], name, ov["high"], ov["mid"], ov["low"], result["judgments"], duration=result["elapsed"]
    )
    return result


@app.post("/api/review_graph/resume")
def review_graph_resume(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    """人工确认后恢复执行：decision 为空 = 全部通过；也可逐条覆盖判定。"""
    tid = str(payload.get("thread_id", ""))
    if user["role"] != "admin" and not tid.startswith(f"rg-{user['id']}-"):
        raise HTTPException(403, "无权操作该任务")
    # 注意：LangGraph 把「空值」当作没有恢复值，所以这里必须给非空结构
    decision = {
        "action": payload.get("action") or "approve",
        "changes": payload.get("changes") or {},
    }

    graph = _get_graph()
    cfg = {"configurable": {"thread_id": tid}}
    snap = graph.get_state(cfg)
    if not snap.values:
        raise HTTPException(404, "任务不存在或已过期")
    if not snap.next:
        raise HTTPException(400, "该任务已结束")

    t0 = time.time()
    try:
        graph.invoke(WF.Command(resume=decision), cfg)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"恢复执行失败：{e}") from e

    snap = graph.get_state(cfg)
    result = _graph_result(snap.values, tid, round(time.time() - t0, 1))
    ov = result["overview"]
    auth.add_review(
        user["id"],
        result["filename"],
        ov["high"],
        ov["mid"],
        ov["low"],
        result["judgments"],
        duration=result["elapsed"],
    )
    return result


@app.post("/api/review")
async def review_upload(
    file: UploadFile = File(...),
    focus: str = Form(""),
    perspective: str = Form(""),
    user: dict = Depends(get_current_user),
) -> dict:
    """上传合同并审查。"""
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "只支持 .docx 文件")

    content = await file.read()
    tmp = config.RAW_DIR.parent / "_api_upload.docx"
    tmp.write_bytes(content)
    t0 = time.time()
    try:
        result = _run_review(tmp, focus, perspective)
    except Exception as e:  # noqa: BLE001
        auth.add_review(
            user["id"], file.filename, 0, 0, 0, None, status="failed", error=str(e)[:300]
        )
        raise HTTPException(500, "审查失败，请联系管理员") from e
    finally:
        tmp.unlink(missing_ok=True)
    dt = time.time() - t0
    result["filename"] = file.filename
    ov = result["overview"]
    auth.add_review(
        user["id"],
        file.filename,
        ov["high"],
        ov["mid"],
        ov["low"],
        result.get("judgments"),
        duration=round(dt, 1),
    )
    return result


@app.post("/api/review_sample")
async def review_sample(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    """按文件名审查示例合同。"""
    name = payload.get("name", "")
    focus = payload.get("focus", "")
    perspective = payload.get("perspective", "")
    path = (config.RAW_DIR / name).resolve()
    # 防路径穿越：必须落在 raw 目录内
    if not str(path).startswith(str(config.RAW_DIR.resolve())) or not path.exists():
        raise HTTPException(404, "合同不存在")
    t0 = time.time()
    try:
        result = _run_review(path, focus, perspective)
    except Exception as e:  # noqa: BLE001
        auth.add_review(user["id"], name, 0, 0, 0, None, status="failed", error=str(e)[:300])
        raise HTTPException(500, "审查失败，请联系管理员") from e
    dt = time.time() - t0
    result["filename"] = name
    ov = result["overview"]
    auth.add_review(
        user["id"], name, ov["high"], ov["mid"], ov["low"], result.get("judgments"), duration=round(dt, 1)
    )
    return result


@app.get("/api/clause_text")
def clause_text(name: str, clause: str, user: dict = Depends(get_current_user)) -> dict:
    """按条款号取合同原文（供对话里点击引用时展示）。"""
    path = (config.RAW_DIR / name).resolve()
    if not str(path).startswith(str(config.RAW_DIR.resolve())) or not path.exists():
        raise HTTPException(404, "合同不存在")

    from src.assess import _find_clause_text
    from src.parser import parse as _parse

    paragraphs = _parse(path)
    text = _find_clause_text(paragraphs, clause, "")
    return {"clause": clause, "text": text or ""}


@app.post("/api/compare")
async def compare_contracts(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    """对比两份合同：各抽 13 类条款，逐条比对差异。"""
    a_name = payload.get("a", "")
    b_name = payload.get("b", "")
    pa = (config.RAW_DIR / a_name).resolve()
    pb = (config.RAW_DIR / b_name).resolve()
    raw_root = str(config.RAW_DIR.resolve())
    for p in (pa, pb):
        if not str(p).startswith(raw_root) or not p.exists():
            raise HTTPException(404, "合同不存在")

    a = _extract_clauses(pa)
    b = _extract_clauses(pb)
    result = _compare(a, b)
    result = _enrich_diffs(result, b_name)
    result.update({"a": a_name, "b": b_name})
    return result


@app.post("/api/compare_upload")
async def compare_upload(
    a_name: str = Form(""),
    b_name: str = Form(""),
    a_file: UploadFile | None = File(None),
    b_file: UploadFile | None = File(None),
    user: dict = Depends(get_current_user),
) -> dict:
    """对比两份合同：支持「样例库合同」与「上传文件」任意组合。"""
    raw_root = config.RAW_DIR.resolve()
    tmpdir = Path(tempfile.mkdtemp(prefix="cmp_"))

    def _resolve(name: str, upload: UploadFile | None, tag: str) -> tuple[Path, str]:
        if upload is not None and upload.filename:
            suffix = Path(upload.filename).suffix.lower() or ".docx"
            if suffix != ".docx":
                raise HTTPException(400, "只支持 .docx 合同")
            dst = tmpdir / f"{tag}{suffix}"
            with dst.open("wb") as fh:
                fh.write(upload.file.read())
            return dst, f"{tag}（上传）"
        if not name:
            raise HTTPException(400, f"请为 {tag} 选择合同或上传文件")
        p = (raw_root / name).resolve()
        if not str(p).startswith(str(raw_root)) or not p.exists():
            raise HTTPException(404, "合同不存在")
        return p, name

    try:
        pa, a_label = _resolve(a_name, a_file, "A")
        pb, b_label = _resolve(b_name, b_file, "B")
        a = _extract_clauses(pa)
        b = _extract_clauses(pb)
        result = _compare(a, b)
        result = _enrich_diffs(result, b_name if not b_file else "")
        result.update({"a": a_label, "b": b_label})
        return result
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _review_context(name: str) -> str:
    """把最近一次审查的结论拼成上下文，供问答回答"哪条高风险"。"""
    r = auth.latest_review(name)
    if not r or not r.get("judgments"):
        return ""
    js = r["judgments"]
    high = [j.get("clause", "") for j in js if j.get("severity") == "高"]
    mid = [j.get("clause", "") for j in js if j.get("severity") == "中"]
    lines = [f"（AI 对话附加信息）这份合同最近一次审查：高风险 {len(high)} 条，中风险 {len(mid)} 条。"]
    if high:
        lines.append("高风险条款：" + "、".join(high))
    if mid:
        lines.append("中风险条款：" + "、".join(mid))
    for j in js:
        if j.get("severity") == "高":
            lines.append(f"- {j.get('clause', '')}：{j.get('verdict', '')}，{str(j.get('reason', ''))[:70]}")
    return "\n".join(lines)


@app.post("/api/chat")
async def chat(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    """基于合同原文的问答（RAG）。"""
    name = payload.get("name", "")
    question = (payload.get("question") or "").strip()
    history = payload.get("history") or []
    if not question:
        raise HTTPException(400, "问题不能为空")

    path = (config.RAW_DIR / name).resolve()
    if not str(path).startswith(str(config.RAW_DIR.resolve())) or not path.exists():
        raise HTTPException(404, "合同不存在")

    return qa.answer_question(path, question, _get_client(), history, _review_context(name))


@app.post("/api/law_chat")
async def law_chat(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    """基于法规库的通用法律问答（RAG），返回带法条引用的回答。"""
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "问题不能为空")
    return law_qa.answer_law_question(question, _get_client(), payload.get("history") or [])


_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@app.post("/api/chat_stream")
async def chat_stream(payload: dict, user: dict = Depends(get_current_user)):
    """合同问答（流式 SSE）。"""
    name = payload.get("name", "")
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "问题不能为空")
    path = (config.RAW_DIR / name).resolve()
    if not str(path).startswith(str(config.RAW_DIR.resolve())) or not path.exists():
        raise HTTPException(404, "合同不存在")
    return StreamingResponse(
        qa.stream_answer_question(
            path, question, _get_client(), payload.get("history") or [], _review_context(name)
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@app.post("/api/law_chat_stream")
async def law_chat_stream(payload: dict, user: dict = Depends(get_current_user)):
    """法律问答（流式 SSE）。"""
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "问题不能为空")
    return StreamingResponse(
        law_qa.stream_answer_law_question(question, _get_client(), payload.get("history") or []),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


# 前端静态文件：优先 Vue 构建产物（frontend/dist），回退到旧版 static/
_DIST = config.ROOT / "frontend" / "dist"
_STATIC = config.ROOT / "static"
app.mount(
    "/",
    StaticFiles(directory=str(_DIST if _DIST.exists() else _STATIC), html=True),
    name="static",
)
