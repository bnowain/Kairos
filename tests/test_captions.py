"""Tests for /api/captions endpoints."""


def test_list_styles(client):
    r = client.get("/api/captions/styles")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_presets(client):
    r = client.get("/api/captions/presets")
    assert r.status_code == 200
    data = r.json()
    assert "tiktok" in data
    assert "youtube" in data
    assert "instagram" in data


def test_create_style(client):
    r = client.post("/api/captions/styles", json={
        "style_name": "Test Style Unique 001",
        "font_name": "Impact",
        "font_size": 64,
        "font_color": "#FFFF00",
        "outline_color": "#000000",
        "outline_width": 3,
        "shadow": 0,
        "position": "bottom",
    })
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["style_name"] == "Test Style Unique 001"
    assert data["font_size"] == 64


def test_create_style_duplicate_name_returns_409(client):
    name = "Unique Style Duplicate Test"
    client.post("/api/captions/styles", json={
        "style_name": name,
        "font_name": "Arial",
        "font_size": 48,
        "font_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "position": "bottom",
    })
    r2 = client.post("/api/captions/styles", json={
        "style_name": name,
        "font_name": "Arial",
        "font_size": 48,
        "font_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "position": "bottom",
    })
    assert r2.status_code == 409


def test_update_style(client):
    r = client.post("/api/captions/styles", json={
        "style_name": "Update Me Style Unique 002",
        "font_name": "Arial",
        "font_size": 48,
        "font_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "position": "bottom",
    })
    assert r.status_code in (200, 201)
    sid = r.json()["style_id"]

    r = client.patch(f"/api/captions/styles/{sid}", json={"font_size": 72})
    assert r.status_code == 200
    assert r.json()["font_size"] == 72


def test_update_style_not_found(client):
    r = client.patch("/api/captions/styles/nonexistent-style-id", json={"font_size": 72})
    assert r.status_code == 404


def test_get_style(client):
    r = client.post("/api/captions/styles", json={
        "style_name": "Get Me Style Unique 003",
        "font_name": "Arial",
        "font_size": 48,
        "font_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "position": "bottom",
    })
    assert r.status_code in (200, 201)
    sid = r.json()["style_id"]

    r = client.get(f"/api/captions/styles/{sid}")
    assert r.status_code == 200
    assert r.json()["style_id"] == sid


def test_get_style_not_found(client):
    r = client.get("/api/captions/styles/nonexistent-style-id")
    assert r.status_code == 404


def test_delete_style(client):
    r = client.post("/api/captions/styles", json={
        "style_name": "Delete Style Unique 004",
        "font_name": "Arial",
        "font_size": 48,
        "font_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "position": "bottom",
    })
    assert r.status_code in (200, 201)
    sid = r.json()["style_id"]

    r = client.delete(f"/api/captions/styles/{sid}")
    assert r.status_code == 200
    data = r.json()
    assert data["deleted"] is True
    assert data["style_id"] == sid


def test_delete_style_not_found(client):
    r = client.delete("/api/captions/styles/nonexistent-style-id")
    assert r.status_code == 404


def test_presets_have_expected_keys(client):
    r = client.get("/api/captions/presets")
    assert r.status_code == 200
    data = r.json()
    for platform in ("tiktok", "youtube", "instagram"):
        preset = data[platform]
        assert "font_name" in preset
        assert "font_size" in preset
        assert "font_color" in preset
        assert "position" in preset


def test_get_single_style_by_id(client):
    """GET /api/captions/styles/{style_id} returns correct style."""
    r = client.post("/api/captions/styles", json={
        "style_name": "Single Style Fetch Test Unique 010",
        "font_name": "Helvetica",
        "font_size": 56,
        "font_color": "#FF0000",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "position": "top",
    })
    assert r.status_code in (200, 201)
    sid = r.json()["style_id"]

    r = client.get(f"/api/captions/styles/{sid}")
    assert r.status_code == 200
    data = r.json()
    assert data["style_name"] == "Single Style Fetch Test Unique 010"
    assert data["font_name"] == "Helvetica"
    assert data["position"] == "top"


def test_get_style_not_found_returns_404(client):
    r = client.get("/api/captions/styles/does-not-exist-style-id")
    assert r.status_code == 404


def test_presets_structure_complete(client):
    """Each preset should have outline_color and outline_width."""
    r = client.get("/api/captions/presets")
    assert r.status_code == 200
    data = r.json()
    for platform in ("tiktok", "youtube", "instagram"):
        preset = data[platform]
        assert "outline_color" in preset
        assert "outline_width" in preset
