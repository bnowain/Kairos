"""Tests for /api/clips endpoints."""


def test_list_clips(client):
    r = client.get("/api/clips")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_clips_filter_item(client, sample_clip, sample_item):
    r = client.get(f"/api/clips?item_id={sample_item}")
    assert r.status_code == 200
    clips = r.json()
    assert any(c["clip_id"] == sample_clip for c in clips)


def test_get_clip(client, sample_clip):
    r = client.get(f"/api/clips/{sample_clip}")
    assert r.status_code == 200
    assert r.json()["clip_id"] == sample_clip


def test_get_clip_not_found(client):
    r = client.get("/api/clips/nonexistent-clip-id")
    assert r.status_code == 404


def test_create_manual_clip_no_file_path_fails(client, sample_item):
    """Creating a clip on an item without file_path should fail with 422."""
    r = client.post("/api/clips", json={
        "item_id": sample_item,
        "start_ms": 1000,
        "end_ms": 11000,
        "clip_title": "My Manual Clip",
    })
    # sample_item has no file_path — expect 422
    assert r.status_code == 422


def test_create_clip_requires_ready_item(client):
    """Creating a clip on a non-ready item should return 422."""
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import MediaItem
    from datetime import datetime

    db = SessionLocal()
    item = MediaItem(
        item_id=str(uuid.uuid4()),
        platform="youtube",
        item_status="queued",
        has_captions=0,
        created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(item)
    db.commit()
    item_id = item.item_id
    db.close()

    r = client.post("/api/clips", json={
        "item_id": item_id,
        "start_ms": 1000,
        "end_ms": 11000,
    })
    assert r.status_code == 422


def test_create_clip_invalid_bounds(client, sample_item):
    """end_ms < start_ms should fail validation."""
    # First we need a ready item with a file_path for real bounds check
    # The 422 here is from start_ms >= end_ms check inside the router
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import MediaItem
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    item = MediaItem(
        item_id=str(uuid.uuid4()),
        platform="local",
        item_status="ready",
        file_path="media_library/test.mp4",
        has_captions=0,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.commit()
    item_id = item.item_id
    db.close()

    r = client.post("/api/clips", json={
        "item_id": item_id,
        "start_ms": 5000,
        "end_ms": 4000,  # end < start
    })
    assert r.status_code == 422


def test_create_clip_with_valid_item(client):
    """Create a clip on an item that has file_path and is ready."""
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import MediaItem
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    item = MediaItem(
        item_id=str(uuid.uuid4()),
        platform="local",
        item_status="ready",
        file_path="media_library/test_valid.mp4",
        has_captions=0,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.commit()
    item_id = item.item_id
    db.close()

    r = client.post("/api/clips", json={
        "item_id": item_id,
        "start_ms": 1000,
        "end_ms": 11000,
        "clip_title": "My Manual Clip",
    })
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["clip_source"] == "manual"
    assert data["duration_ms"] == 10000


def test_update_clip_title(client, sample_clip):
    r = client.patch(f"/api/clips/{sample_clip}", json={"clip_title": "Updated Title"})
    assert r.status_code == 200
    assert r.json()["clip_title"] == "Updated Title"


def test_update_clip_not_found(client):
    r = client.patch("/api/clips/nonexistent-clip-id", json={"clip_title": "X"})
    assert r.status_code == 404


def test_delete_clip(client, sample_item):
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import Clip
    from datetime import datetime

    db = SessionLocal()
    clip = Clip(
        clip_id=str(uuid.uuid4()),
        item_id=sample_item,
        start_ms=0,
        end_ms=5000,
        duration_ms=5000,
        clip_status="pending",
        clip_source="manual",
        created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(clip)
    db.commit()
    clip_id = clip.clip_id
    db.close()

    r = client.delete(f"/api/clips/{clip_id}")
    assert r.status_code == 200


def test_delete_clip_not_found(client):
    r = client.delete("/api/clips/nonexistent-clip-id")
    assert r.status_code == 404


def test_batch_extract(client):
    r = client.post("/api/clips/batch/extract", json={})
    assert r.status_code == 200
    assert "enqueued" in r.json()


def test_list_clips_filter_status(client, sample_clip):
    r = client.get("/api/clips?status=ready")
    assert r.status_code == 200
    clips = r.json()
    assert all(c["clip_status"] == "ready" for c in clips)


def test_list_clips_filter_source(client, sample_clip):
    r = client.get("/api/clips?source=ai")
    assert r.status_code == 200
    clips = r.json()
    assert all(c["clip_source"] == "ai" for c in clips)
