"""Tests for /api/acquisition endpoints."""


def test_list_sources_empty(client):
    r = client.get("/api/acquisition/sources")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_source(client):
    r = client.post("/api/acquisition/sources", json={
        "source_type": "youtube_channel",
        "source_url": "https://youtube.com/@testchannel",
        "source_name": "Test Channel",
        "platform": "youtube",
    })
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["source_name"] == "Test Channel"
    assert data["platform"] == "youtube"


def test_create_source_duplicate_returns_409(client):
    """Creating the same URL twice should return 409."""
    url = "https://youtube.com/@duplicate_test_unique"
    client.post("/api/acquisition/sources", json={
        "source_type": "youtube_channel",
        "source_url": url,
        "platform": "youtube",
    })
    r2 = client.post("/api/acquisition/sources", json={
        "source_type": "youtube_channel",
        "source_url": url,
        "platform": "youtube",
    })
    assert r2.status_code == 409


def test_update_source(client):
    # Create first
    r = client.post("/api/acquisition/sources", json={
        "source_type": "youtube_channel",
        "source_url": "https://youtube.com/@updatetest_unique",
        "platform": "youtube",
    })
    assert r.status_code in (200, 201)
    sid = r.json()["source_id"]
    # Update
    r = client.put(f"/api/acquisition/sources/{sid}", json={"enabled": 0})
    assert r.status_code == 200
    assert r.json()["enabled"] == 0


def test_update_source_not_found(client):
    r = client.put("/api/acquisition/sources/nonexistent-id", json={"enabled": 0})
    assert r.status_code == 404


def test_delete_source(client):
    r = client.post("/api/acquisition/sources", json={
        "source_type": "youtube_channel",
        "source_url": "https://youtube.com/@deletetest_unique",
        "platform": "youtube",
    })
    assert r.status_code in (200, 201)
    sid = r.json()["source_id"]
    r = client.delete(f"/api/acquisition/sources/{sid}")
    # 204 No Content or 200
    assert r.status_code in (200, 204)
    # Verify gone
    r = client.get("/api/acquisition/sources")
    ids = [s["source_id"] for s in r.json()]
    assert sid not in ids


def test_delete_source_not_found(client):
    r = client.delete("/api/acquisition/sources/nonexistent-id")
    assert r.status_code == 404


def test_download_request_creates_item(client):
    """POST /api/acquisition/download should create a MediaItem (without actually downloading)."""
    r = client.post("/api/acquisition/download", json={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    })
    # May be 200 or 202
    assert r.status_code in (200, 202)
    data = r.json()
    assert "item_id" in data
    assert data["status"] == "queued"
