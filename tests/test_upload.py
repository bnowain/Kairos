"""Tests for /api/acquisition/upload endpoint."""

import io


def test_upload_video_file(client):
    """Upload a video file should return 202 with item_id."""
    file_content = b"\x00\x00\x00\x1c" + b"ftyp" + b"\x00" * 100  # minimal mp4-like bytes
    r = client.post(
        "/api/acquisition/upload",
        files={"file": ("test_video.mp4", io.BytesIO(file_content), "video/mp4")},
    )
    assert r.status_code == 202
    data = r.json()
    assert "item_id" in data
    assert data["status"] == "ingesting"


def test_upload_creates_media_item(client):
    """Uploaded file creates a media item in the library."""
    file_content = b"\x00" * 64
    r = client.post(
        "/api/acquisition/upload",
        files={"file": ("library_check.mp4", io.BytesIO(file_content), "video/mp4")},
    )
    assert r.status_code == 202
    item_id = r.json()["item_id"]

    r = client.get(f"/api/library/{item_id}")
    assert r.status_code == 200
    assert r.json()["platform"] == "local"


def test_upload_with_title(client):
    """Upload with explicit title uses it instead of filename."""
    file_content = b"\x00" * 64
    r = client.post(
        "/api/acquisition/upload",
        files={"file": ("raw_file.mp4", io.BytesIO(file_content), "video/mp4")},
        data={"title": "My Custom Title"},
    )
    assert r.status_code == 202
    item_id = r.json()["item_id"]

    r = client.get(f"/api/library/{item_id}")
    assert r.status_code == 200
    assert r.json()["item_title"] == "My Custom Title"


def test_upload_without_title_uses_filename(client):
    """Upload without title falls back to original filename."""
    file_content = b"\x00" * 64
    r = client.post(
        "/api/acquisition/upload",
        files={"file": ("my_recording.mp4", io.BytesIO(file_content), "video/mp4")},
    )
    assert r.status_code == 202
    item_id = r.json()["item_id"]

    r = client.get(f"/api/library/{item_id}")
    assert r.status_code == 200
    assert r.json()["item_title"] == "my_recording.mp4"


def test_upload_item_status_after_upload(client):
    """After upload, item status should reflect ingest has started."""
    file_content = b"\x00" * 64
    r = client.post(
        "/api/acquisition/upload",
        files={"file": ("status_check.mp4", io.BytesIO(file_content), "video/mp4")},
    )
    assert r.status_code == 202
    item_id = r.json()["item_id"]

    r = client.get(f"/api/library/{item_id}")
    assert r.status_code == 200
    # Status should be "downloaded" (set before ingest_task runs) or "ingesting"
    assert r.json()["item_status"] in ("downloaded", "ingesting", "ready", "error")


def test_upload_missing_file(client):
    """Upload without a file should return 422."""
    r = client.post("/api/acquisition/upload")
    assert r.status_code == 422
