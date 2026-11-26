"""审查记录接口：列表隔离、详情权限、删除权限、健康检查。"""

import src.auth as auth
from conftest import unique


def _mk_user(client, prefix: str = "u"):
    """在同一个测试里创建多个用户（fixture 在同一测试内会缓存，不能复用）。"""
    name = unique(prefix)
    r = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    body = r.json()
    return {"Authorization": f"Bearer {body['token']}"}, body["user"]["id"]


def _seed_review(user_id: int, filename: str = "测试合同.docx") -> int:
    auth.add_review(user_id, filename, 2, 3, 1, judgments=[{"clause": "付款条款", "severity": "高"}])
    rows = auth.list_reviews(user_id)
    return rows[0]["id"]


def test_reviews_empty_for_new_user(client, new_user):
    headers, _, _ = new_user
    r = client.get("/api/reviews", headers=headers)
    assert r.status_code == 200
    assert r.json()["reviews"] == []


def test_reviews_only_own_records(client, new_user):
    headers, _, uid = new_user
    _seed_review(uid, "我的合同.docx")
    rows = client.get("/api/reviews", headers=headers).json()["reviews"]
    assert len(rows) == 1
    assert rows[0]["filename"] == "我的合同.docx"
    assert "category" in rows[0]


def test_review_detail_ok_for_owner(client, new_user):
    headers, _, uid = new_user
    rid = _seed_review(uid, "详情合同.docx")
    r = client.get(f"/api/reviews/{rid}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["filename"] == "详情合同.docx"
    assert isinstance(body["judgments"], list)


def test_review_detail_forbidden_for_others(client):
    headers_a, uid_a = _mk_user(client, "a")
    headers_b, _ = _mk_user(client, "b")
    rid = _seed_review(uid_a)
    r = client.get(f"/api/reviews/{rid}", headers=headers_b)
    assert r.status_code == 403


def test_review_detail_404(client, admin_headers):
    assert client.get("/api/reviews/999999", headers=admin_headers).status_code == 404


def test_admin_can_delete_review(client, admin_headers, new_user):
    _, _, uid = new_user
    rid = _seed_review(uid)
    assert client.delete(f"/api/reviews/{rid}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/reviews/{rid}", headers=admin_headers).status_code == 404


def test_health_contains_services(client, admin_headers):
    r = client.get("/api/admin/health", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "services" in body
    assert set(body["services"]) == {"db", "llm", "files"}
    assert body["services"]["db"] is True


def test_me_stats_shape(client, new_user):
    headers, _, uid = new_user
    _seed_review(uid, "买卖合同_测试.docx")
    r = client.get("/api/me/stats", headers=headers)
    assert r.status_code == 200
    body = r.json()
    for key in ("total", "high", "mid", "low", "by_category", "type_profiles"):
        assert key in body
    assert body["total"] >= 1
