"""Spec CRUD endpoint 测试。"""


def test_list_specs(client):
    r = client.get("/api/specs")
    assert r.status_code == 200
    d = r.json()
    assert "specs" in d
    assert len(d["specs"]) >= 8  # 至少 8 个真实 spec
    one = d["specs"][0]
    assert {"id", "module", "level_id", "mtime"} <= set(one.keys())


def test_get_spec_ok(client):
    r = client.get("/api/specs/lighting_req_underground_parking_horror")
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == "lighting_req_underground_parking_horror"
    assert d["module"] == "lighting_req"
    assert "meta" in d["content"]


def test_get_spec_404(client):
    r = client.get("/api/specs/nonexistent_smoke_xxx_abc")
    assert r.status_code == 404


def test_get_spec_invalid_id(client):
    # spec_id 含非法字符（路径穿越尝试），URL 转义后仍应被 SpecInvalid 挡下
    r = client.get("/api/specs/..%2Fetc")
    assert r.status_code in (400, 404)


def test_save_and_delete(client, cleanup_smoke_specs):
    spec_id = "test_smoke_save_lighting"
    payload = {"content": {
        "meta": {"spec_id": spec_id, "level_id": "test_smoke", "version": "0.1.0"},
        "intent": "smoke test save",
    }}
    r = client.put(f"/api/specs/{spec_id}", json=payload)
    assert r.status_code == 200
    assert r.json()["id"] == spec_id
    assert r.json()["mtime"] > 0

    r2 = client.get(f"/api/specs/{spec_id}")
    assert r2.status_code == 200
    assert r2.json()["content"]["meta"]["spec_id"] == spec_id

    r3 = client.delete(f"/api/specs/{spec_id}")
    assert r3.status_code == 200
    assert r3.json()["ok"] is True

    r4 = client.get(f"/api/specs/{spec_id}")
    assert r4.status_code == 404


def test_delete_not_found(client):
    r = client.delete("/api/specs/test_smoke_nonexistent_xxx")
    assert r.status_code == 404
