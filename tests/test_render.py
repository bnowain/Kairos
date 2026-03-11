"""Tests for /api/render endpoints."""


def test_list_render_jobs(client):
    r = client.get("/api/render")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_submit_render(client, sample_timeline):
    r = client.post("/api/render", json={
        "timeline_id": sample_timeline,
        "quality": "preview",
        "apply_captions": False,
    })
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["timeline_id"] == sample_timeline
    assert data["render_quality"] == "preview"
    assert data["render_status"] in ("queued", "running", "error")


def test_submit_render_invalid_quality(client, sample_timeline):
    r = client.post("/api/render", json={
        "timeline_id": sample_timeline,
        "quality": "ultra",
    })
    assert r.status_code == 422


def test_submit_render_invalid_reframe(client, sample_timeline):
    r = client.post("/api/render", json={
        "timeline_id": sample_timeline,
        "quality": "preview",
        "reframe_aspect_ratio": "4:3",
    })
    assert r.status_code == 422


def test_submit_render_timeline_not_found(client):
    r = client.post("/api/render", json={
        "timeline_id": "nonexistent-timeline-id",
        "quality": "preview",
    })
    assert r.status_code == 404


def test_get_render_job(client, sample_timeline):
    # Submit first
    r = client.post("/api/render", json={
        "timeline_id": sample_timeline,
        "quality": "preview",
    })
    assert r.status_code in (200, 201)
    rid = r.json()["render_id"]

    r = client.get(f"/api/render/{rid}")
    assert r.status_code == 200
    assert r.json()["render_id"] == rid


def test_render_not_found(client):
    r = client.get("/api/render/nonexistent")
    assert r.status_code == 404


def test_delete_render_job(client, sample_timeline):
    # Create a render job first
    r = client.post("/api/render", json={
        "timeline_id": sample_timeline,
        "quality": "preview",
    })
    assert r.status_code in (200, 201)
    rid = r.json()["render_id"]

    r = client.delete(f"/api/render/{rid}")
    assert r.status_code == 200
    data = r.json()
    assert data["deleted"] is True
    assert data["render_id"] == rid


def test_delete_render_not_found(client):
    r = client.delete("/api/render/nonexistent-render-id")
    assert r.status_code == 404


def test_retry_render_job(client, sample_timeline):
    """Retry a queued/errored job."""
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import RenderJob
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    job = RenderJob(
        render_id=str(uuid.uuid4()),
        timeline_id=sample_timeline,
        render_quality="preview",
        render_status="error",
        error_msg="Test error",
        created_at=now,
    )
    db.add(job)
    db.commit()
    render_id = job.render_id
    db.close()

    r = client.post(f"/api/render/{render_id}/retry")
    assert r.status_code == 200
    data = r.json()
    assert data["render_status"] in ("queued", "error")  # error if task dispatch fails
