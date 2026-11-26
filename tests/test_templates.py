"""模板库与静态接口。"""


def test_root_serves_frontend(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "assets/" in r.text or "root" in r.text.lower()


def test_contracts_list(client, admin_headers):
    r = client.get("/api/contracts", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json()["contracts"], list)


def test_templates_list(client, admin_headers):
    r = client.get("/api/templates", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()["templates"]
    assert isinstance(items, list)
    if items:
        assert {"name", "title", "category", "clause_count"} <= set(items[0])
