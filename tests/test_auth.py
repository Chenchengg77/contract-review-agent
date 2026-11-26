"""认证相关：注册 / 登录 / 禁用 / 改密 / 找回密码。"""

from conftest import unique


def test_register_ok(client):
    name = unique("reg")
    r = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["username"] == name
    assert body["token"]


def test_register_duplicate_username(client):
    name = unique("dup")
    assert client.post("/api/auth/register", json={"username": name, "password": "pass1234"}).status_code == 200
    r = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert r.status_code == 400


def test_register_short_password(client):
    r = client.post("/api/auth/register", json={"username": unique("sp"), "password": "123"})
    assert r.status_code == 400


def test_login_ok(client):
    name = unique("lg")
    client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    r = client.post("/api/auth/login", json={"username": name, "password": "pass1234"})
    assert r.status_code == 200
    assert r.json()["user"]["username"] == name


def test_login_wrong_password(client):
    name = unique("wp")
    client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    r = client.post("/api/auth/login", json={"username": name, "password": "wrongpass"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/auth/login", json={"username": "no_such_user_xyz", "password": "pass1234"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_current_user(client, new_user):
    headers, name, _ = new_user
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] == name
    assert "has_security_question" in r.json()


# ---- 禁用账号 ----
def test_disabled_user_cannot_login(client, admin_headers, new_user):
    headers, name, uid = new_user
    # 正常可登录
    assert client.post("/api/auth/login", json={"username": name, "password": "pass1234"}).status_code == 200
    # 管理员禁用
    r = client.patch(f"/api/admin/users/{uid}/status", json={"status": "disabled"}, headers=admin_headers)
    assert r.status_code == 200
    # 禁用后登录被拒
    r = client.post("/api/auth/login", json={"username": name, "password": "pass1234"})
    assert r.status_code == 403


def test_cannot_disable_self(client, admin_headers):
    me = client.get("/api/auth/me", headers=admin_headers).json()
    r = client.patch(f"/api/admin/users/{me['id']}/status", json={"status": "disabled"}, headers=admin_headers)
    assert r.status_code == 400


# ---- 修改密码 ----
def test_change_password_requires_correct_old(client, new_user):
    headers, name, _ = new_user
    r = client.post(
        "/api/auth/change-password",
        json={"old_password": "wrong", "new_password": "newpass99"},
        headers=headers,
    )
    assert r.status_code == 400


def test_change_password_ok(client, new_user):
    headers, name, _ = new_user
    r = client.post(
        "/api/auth/change-password",
        json={"old_password": "pass1234", "new_password": "newpass99"},
        headers=headers,
    )
    assert r.status_code == 200
    # 旧密码失效
    assert client.post("/api/auth/login", json={"username": name, "password": "pass1234"}).status_code == 401
    # 新密码可用
    assert client.post("/api/auth/login", json={"username": name, "password": "newpass99"}).status_code == 200


def test_change_password_too_short(client, new_user):
    headers, _, _ = new_user
    r = client.post(
        "/api/auth/change-password",
        json={"old_password": "pass1234", "new_password": "123"},
        headers=headers,
    )
    assert r.status_code == 400


# ---- 找回密码（安全问题）----
def test_forgot_password_flow(client):
    name = unique("fg")
    question = "我的第一份合同编号"
    r = client.post(
        "/api/auth/register",
        json={
            "username": name,
            "password": "pass1234",
            "security_question": question,
            "security_answer": "HT-001",
        },
    )
    assert r.status_code == 200

    # 1) 取回问题
    r = client.post("/api/auth/forgot/question", json={"username": name})
    assert r.status_code == 200
    assert r.json()["question"] == question

    # 2) 答案错误
    r = client.post(
        "/api/auth/forgot/reset",
        json={"username": name, "answer": "wrong", "new_password": "reset123"},
    )
    assert r.status_code == 400

    # 3) 答案正确（大小写不敏感）
    r = client.post(
        "/api/auth/forgot/reset",
        json={"username": name, "answer": "ht-001", "new_password": "reset123"},
    )
    assert r.status_code == 200

    # 4) 新密码可登录，旧密码失效
    assert client.post("/api/auth/login", json={"username": name, "password": "reset123"}).status_code == 200
    assert client.post("/api/auth/login", json={"username": name, "password": "pass1234"}).status_code == 401


def test_forgot_unknown_user(client):
    r = client.post("/api/auth/forgot/question", json={"username": "no_such_user_abc"})
    assert r.status_code == 404


def test_forgot_without_question(client):
    """没设安全问题的账号：提示联系管理员，而不是假装能重置。"""
    name = unique("nq")
    client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    r = client.post("/api/auth/forgot/question", json={"username": name})
    assert r.status_code == 400


def test_set_security_question_when_logged_in(client, new_user):
    headers, _, _ = new_user
    r = client.post(
        "/api/auth/security-question",
        json={"question": "我最喜欢的合同类型", "answer": "买卖"},
        headers=headers,
    )
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=headers).json()["has_security_question"] is True
