"""Tests for /api/library endpoints."""


def test_list_library(client):
    r = client.get("/api/library")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_library_filter_status(client, sample_item):
    r = client.get("/api/library?status=ready")
    assert r.status_code == 200
    items = r.json()
    assert all(i["item_status"] == "ready" for i in items)


def test_get_item_detail(client, sample_item):
    r = client.get(f"/api/library/{sample_item}")
    assert r.status_code == 200
    data = r.json()
    assert data["item_id"] == sample_item
    assert data["item_title"] == "Test Video"
    assert "segment_count" in data


def test_get_item_not_found(client):
    r = client.get("/api/library/nonexistent-id")
    assert r.status_code == 404


def test_delete_item(client):
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import MediaItem
    from datetime import datetime

    db = SessionLocal()
    item = MediaItem(
        item_id=str(uuid.uuid4()),
        platform="local",
        item_status="ready",
        has_captions=0,
        created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(item)
    db.commit()
    item_id = item.item_id
    db.close()

    r = client.delete(f"/api/library/{item_id}")
    assert r.status_code in (200, 204)


def test_delete_item_not_found(client):
    r = client.delete("/api/library/nonexistent-id")
    assert r.status_code == 404


def test_list_library_filter_platform(client, sample_item):
    r = client.get("/api/library?platform=youtube")
    assert r.status_code == 200
    items = r.json()
    assert all(i["platform"] == "youtube" for i in items)


def test_list_library_pagination(client):
    r = client.get("/api/library?limit=1&offset=0")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) <= 1
