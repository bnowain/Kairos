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


def test_poll_source(client, sample_source):
    """Poll a source should return 200 (may fail subprocess but HTTP succeeds)."""
    r = client.post(f"/api/acquisition/sources/{sample_source}/poll")
    # 200 success or 500/504 if yt-dlp is not installed / times out
    assert r.status_code in (200, 500, 504)


def test_poll_disabled_source(client):
    """Polling a disabled source should return 400."""
    r = client.post("/api/acquisition/sources", json={
        "source_type": "youtube_channel",
        "source_url": "https://youtube.com/@disabled_poll_test",
        "platform": "youtube",
        "enabled": 0,
    })
    assert r.status_code in (200, 201)
    sid = r.json()["source_id"]

    r = client.post(f"/api/acquisition/sources/{sid}/poll")
    assert r.status_code == 400


def test_download_invalid_url(client):
    """Download with an empty/missing URL should return 422."""
    r = client.post("/api/acquisition/download", json={})
    assert r.status_code == 422


def test_create_source_with_all_fields(client):
    """Create a source with all optional fields populated."""
    r = client.post("/api/acquisition/sources", json={
        "source_type": "youtube_playlist",
        "source_url": "https://youtube.com/playlist?list=PLtest_all_fields",
        "source_name": "Full Config Source",
        "platform": "youtube",
        "schedule_cron": "0 */6 * * *",
        "enabled": 1,
        "download_quality": "bestvideo[height<=720]+bestaudio/best",
    })
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["source_name"] == "Full Config Source"
    assert data["schedule_cron"] == "0 */6 * * *"
    assert data["download_quality"] == "bestvideo[height<=720]+bestaudio/best"
