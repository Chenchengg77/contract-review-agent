"""pytest 公共配置：用临时数据库跑测试，绝不碰 data/app.db。"""

import sys
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---- 关键：先把 DB_PATH 指到临时文件，再导入 api（导入时会建表 + 建 admin/demo）----
_TMP = Path(tempfile.mkdtemp(prefix="cr_test_"))

import src.auth as auth  # noqa: E402

auth.DB_PATH = _TMP / "test.db"

import api  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_seq = {"n": 0}


def unique(prefix: str = "u") -> str:
    _seq["n"] += 1
    return f"{prefix}{int(time.time() * 1000) % 1_000_000}{_seq['n']}"


@pytest.fixture(scope="session")
def client():
    with TestClient(api.app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_headers(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture
def new_user(client):
    """注册一个普通用户，返回 (headers, username, user_id)。"""
    name = unique("t")
    r = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert r.status_code == 200, r.text
    body = r.json()
    return {"Authorization": f"Bearer {body['token']}"}, name, body["user"]["id"]
