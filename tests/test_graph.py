"""LangGraph 接口的权限与生命周期（不调用大模型）。"""

from conftest import unique

from src.workflow import new_app


def test_graph_has_revise_and_confirm_nodes():
    """主链路节点齐全：抽取→判定→修订→确认→报告。"""
    g = new_app().get_graph()
    nodes = set(g.nodes.keys())
    for name in ("parse", "extract", "assess", "revise", "confirm", "report"):
        assert name in nodes, f"缺少节点 {name}"


def _mk(client, prefix="g"):
    name = unique(prefix)
    r = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    body = r.json()
    return {"Authorization": f"Bearer {body['token']}"}, body["user"]["id"]


def test_resume_rejects_other_users_thread(client):
    headers, _ = _mk(client, "ga")
    _, other_id = _mk(client, "gb")
    r = client.post(
        "/api/review_graph/resume",
        json={"thread_id": f"rg-{other_id}-abcdef12", "action": "approve"},
        headers=headers,
    )
    assert r.status_code == 403


def test_resume_unknown_thread_returns_404(client):
    headers, uid = _mk(client, "gc")
    r = client.post(
        "/api/review_graph/resume",
        json={"thread_id": f"rg-{uid}-notexist", "action": "approve"},
        headers=headers,
    )
    assert r.status_code == 404


def test_review_graph_rejects_missing_contract(client, new_user):
    headers, _, _ = new_user
    r = client.post("/api/review_graph", data={"name": "不存在的合同.docx"}, headers=headers)
    assert r.status_code == 404


def test_review_graph_requires_login(client):
    r = client.post("/api/review_graph", data={"name": "x.docx"})
    assert r.status_code == 401
