"""check / cross-check / render / modules endpoint 测试。"""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert d["agent_backend"] in ("local", "remote")


def test_modules(client):
    r = client.get("/api/modules")
    assert r.status_code == 200
    d = r.json()
    assert len(d["modules"]) == 8
    names = {m["name"] for m in d["modules"]}
    assert {"lighting_req", "spatial_layout", "bubble_diagram"} <= names


def test_module_schema(client):
    r = client.get("/api/modules/lighting_req/schema")
    assert r.status_code == 200
    schema = r.json()
    assert schema.get("type") == "object"


def test_module_schema_404(client):
    r = client.get("/api/modules/nonexistent/schema")
    assert r.status_code == 404


def test_paths_compat(client):
    r = client.get("/api/paths", params={"spec": "lighting_req_underground_parking_horror"})
    assert r.status_code == 200
    d = r.json()
    assert d["spec"].endswith(".spec.json")
    assert d["schema_path"].endswith("lighting_req.schema.json")
    assert d["template"].endswith(".html.tmpl")


def test_check_ok(client):
    r = client.post("/api/check", json={"spec_id": "lighting_req_underground_parking_horror"})
    assert r.status_code == 200
    d = r.json()
    assert d["mechanical"]["stats"]["errors"] == 0
    assert d["template"]["stats"]["mapped"] == 7


def test_check_404(client):
    r = client.post("/api/check", json={"spec_id": "nonexistent_smoke_xxx"})
    assert r.status_code == 404


def test_cross_check_ok(client):
    r = client.post("/api/cross-check", json={"level_id": "abandoned_temple"})
    assert r.status_code == 200
    d = r.json()
    assert "stats" in d
    assert d["stats"]["errors"] == 0


def test_cross_check_empty(client):
    r = client.post("/api/cross-check", json={"level_id": "nonexistent_smoke_lvl"})
    assert r.status_code == 200
    d = r.json()
    assert "warning" in d


def test_render_spec(client):
    r = client.post("/api/render", json={"spec_id": "lighting_req_underground_parking_horror"})
    assert r.status_code == 200
    d = r.json()
    assert d["spec_id"] == "lighting_req_underground_parking_horror"
    assert d["output_path"].endswith(".html")
    assert d["size_bytes"] > 0


def test_render_level(client):
    r = client.post("/api/render-level", json={"level_id": "abandoned_temple", "render_missing": True})
    assert r.status_code == 200
    d = r.json()
    assert d["level_id"] == "abandoned_temple"
    assert d["output_path"].endswith("__full.html")
    assert len(d["modules"]) == 8


def test_render_level_404_spec_missing(client):
    r = client.post("/api/render-level", json={"level_id": "nonexistent_smoke_lvl"})
    assert r.status_code == 400  # ValueError -> 400


def test_render_deck(client):
    r = client.post("/api/render-deck", json={"level_id": "abandoned_temple"})
    assert r.status_code == 200
    d = r.json()
    assert d["output_path"].endswith("__deck.html")
