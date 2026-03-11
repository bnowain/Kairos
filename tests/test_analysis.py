"""Tests for /api/analysis endpoints."""


def test_analysis_start_no_segments(client, sample_item):
    """sample_item has no transcription segments — should return 422."""
    r = client.post(f"/api/analysis/{sample_item}/start")
    assert r.status_code == 422


def test_analysis_start_item_not_found(client):
    r = client.post("/api/analysis/nonexistent-item/start")
    assert r.status_code == 404


def test_analysis_status(client, sample_item):
    r = client.get(f"/api/analysis/{sample_item}/status")
    assert r.status_code == 200
    data = r.json()
    assert "item_id" in data
    assert "analysis_status" in data
    assert "segment_count" in data


def test_analysis_status_not_found(client):
    r = client.get("/api/analysis/nonexistent-item/status")
    assert r.status_code == 404


def test_analysis_scores_empty(client, sample_item):
    r = client.get(f"/api/analysis/{sample_item}/scores")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_analysis_highlights_empty(client, sample_item):
    r = client.get(f"/api/analysis/{sample_item}/highlights")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_analysis_start_with_segments(client):
    """Item with segments and ready status — should return 202."""
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import MediaItem, TranscriptionJob, TranscriptionSegment
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    item = MediaItem(
        item_id=str(uuid.uuid4()),
        platform="youtube",
        item_status="ready",
        has_captions=1,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.commit()

    job = TranscriptionJob(
        job_id=str(uuid.uuid4()),
        item_id=item.item_id,
        job_status="done",
        created_at=now,
    )
    db.add(job)
    db.commit()

    seg = TranscriptionSegment(
        segment_id=str(uuid.uuid4()),
        item_id=item.item_id,
        job_id=job.job_id,
        start_ms=0,
        end_ms=5000,
        segment_text="Hello this is a test segment.",
        created_at=now,
    )
    db.add(seg)
    db.commit()
    item_id = item.item_id
    db.close()

    r = client.post(f"/api/analysis/{item_id}/start")
    # Should succeed (202) since segments exist and item is ready
    assert r.status_code == 202
    data = r.json()
    assert data["item_id"] == item_id
    assert data["status"] == "queued"


def test_analysis_generate_clips_no_scores(client, sample_item):
    """Generating clips when no analysis scores exist should return 0 clips."""
    r = client.post(f"/api/analysis/{sample_item}/clips/generate")
    # Either returns 0 clips created or 404 if item not found (it exists)
    assert r.status_code in (200, 201)
    data = r.json()
    assert data.get("clips_created", 0) == 0
