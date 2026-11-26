"""权限：普通用户不能进管理端，未登录不能访问受保护接口。"""


ADMIN_ONLY = [
    ("GET", "/api/admin/stats"),
    ("GET", "/api/admin/users"),
    ("GET", "/api/admin/health"),
    ("GET", "/api/admin/failures"),
    ("GET", "/api/admin/settings"),
]


def test_anonymous_is_rejected(client):
    for method, path in ADMIN_ONLY:
        r = client.request(method, path)
        assert r.status_code == 401, f"{method} {path} 应返回 401，实际 {r.status_code}"


def test_normal_user_cannot_access_admin(client, new_user):
    headers, _, _ = new_user
    for method, path in ADMIN_ONLY:
        r = client.request(method, path, headers=headers)
        assert r.status_code == 403, f"{method} {path} 应返回 403，实际 {r.status_code}"


def test_admin_can_access_admin(client, admin_headers):
    for method, path in ADMIN_ONLY:
        r = client.request(method, path, headers=admin_headers)
        assert r.status_code == 200, f"{method} {path} 应返回 200，实际 {r.status_code}"


def test_normal_user_cannot_delete_review(client, new_user):
    headers, _, _ = new_user
    assert client.delete("/api/reviews/1", headers=headers).status_code == 403


def test_normal_user_cannot_create_user(client, new_user):
    headers, _, _ = new_user
    r = client.post(
        "/api/admin/users",
        json={"username": "hacker", "password": "pass1234"},
        headers=headers,
    )
    assert r.status_code == 403
