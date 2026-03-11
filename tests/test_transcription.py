"""Tests for /api/transcription endpoints."""


def test_transcription_start_requires_audio_path(client, sample_item):
    """sample_item has no audio_path — should return 422."""
    r = client.post(f"/api/transcription/{sample_item}/start")
    # item is ready but has no audio_path — expect 422
    assert r.status_code == 422


def test_transcription_start_item_not_found(client):
    r = client.post("/api/transcription/nonexistent-item/start")
    assert r.status_code == 404


def test_transcription_status_not_found(client):
    """No job exists for this item yet."""
    r = client.get("/api/transcription/nonexistent/status")
    assert r.status_code == 404


def test_transcription_status_after_start(client):
    """Create an item with audio_path and start transcription, then check status."""
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import MediaItem, TranscriptionJob
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    item = MediaItem(
        item_id=str(uuid.uuid4()),
        platform="youtube",
        item_status="ready",
        has_captions=0,
        audio_path="audio/fake_audio.wav",
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    # Also create a transcription job to check status endpoint
    job = TranscriptionJob(
        job_id=str(uuid.uuid4()),
        item_id=item.item_id,
        job_status="queued",
        created_at=now,
    )
    db.add(job)
    db.commit()
    item_id = item.item_id
    db.close()

    r = client.get(f"/api/transcription/{item_id}/status")
    assert r.status_code == 200
    data = r.json()
    assert data["item_id"] == item_id
    assert "job_status" in data
    assert "segment_count" in data


def test_transcription_segments_empty(client, sample_item):
    """No segments exist for this item yet."""
    r = client.get(f"/api/transcription/{sample_item}/segments")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) == 0


def test_transcription_export_no_segments(client, sample_item):
    """Export with no segments should return 404 (file doesn't exist)."""
    r = client.get(f"/api/transcription/{sample_item}/export/srt")
    assert r.status_code == 404


def test_transcription_export_invalid_format(client, sample_item):
    r = client.get(f"/api/transcription/{sample_item}/export/xml")
    assert r.status_code == 400


def test_transcription_delete(client):
    """Delete transcription for an item with a job."""
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import MediaItem, TranscriptionJob
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    item = MediaItem(
        item_id=str(uuid.uuid4()),
        platform="local",
        item_status="ready",
        has_captions=0,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    job = TranscriptionJob(
        job_id=str(uuid.uuid4()),
        item_id=item.item_id,
        job_status="done",
        created_at=now,
    )
    db.add(job)
    db.commit()
    item_id = item.item_id
    db.close()

    r = client.delete(f"/api/transcription/{item_id}")
    assert r.status_code == 200
    data = r.json()
    assert "deleted_jobs" in data
    assert data["item_id"] == item_id
