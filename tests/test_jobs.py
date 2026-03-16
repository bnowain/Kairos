"""Tests for /api/jobs endpoints."""


def test_create_quick_job(client):
    r = client.post("/api/jobs/quick", json={
        "urls": ["https://youtube.com/watch?v=abc123"],
        "template_id": "viral_reel",
        "aspect_ratio": "9:16",
    })
    assert r.status_code == 202
    data = r.json()
    assert data["job_status"] == "queued"
    assert "job_id" in data


def test_create_quick_job_empty_urls(client):
    r = client.post("/api/jobs/quick", json={
        "urls": [],
        "template_id": "viral_reel",
    })
    assert r.status_code == 422


def test_list_quick_jobs(client, sample_quick_job):
    """GET /api/jobs returns a list (system jobs endpoint)."""
    r = client.get("/api/jobs")
    assert r.status_code == 200
    jobs = r.json()
    assert isinstance(jobs, list)
    # Verify the fixture job is accessible via the detail endpoint
    r2 = client.get(f"/api/jobs/{sample_quick_job}")
    assert r2.status_code == 200
    assert r2.json()["job_id"] == sample_quick_job


def test_get_quick_job(client, sample_quick_job):
    r = client.get(f"/api/jobs/{sample_quick_job}")
    assert r.status_code == 200
    assert r.json()["job_id"] == sample_quick_job
    assert r.json()["job_status"] == "error"


def test_get_quick_job_not_found(client):
    r = client.get("/api/jobs/nonexistent-job-id")
    assert r.status_code == 404


def test_retry_error_job(client, sample_quick_job):
    r = client.post(f"/api/jobs/{sample_quick_job}/retry")
    assert r.status_code == 200
    data = r.json()
    assert data["job_status"] == "queued"
    assert data["error_msg"] is None


def test_retry_running_job(client):
    """Cannot retry a job that is currently running."""
    import uuid
    import json
    from kairos.database import SessionLocal
    from kairos.models import QuickJob
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    job = QuickJob(
        job_id=str(uuid.uuid4()),
        urls=json.dumps(["https://youtube.com/watch?v=running"]),
        template_id="viral_reel",
        aspect_ratio="9:16",
        job_status="downloading",
        stage_label="Downloading...",
        progress=30,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    job_id = job.job_id
    db.close()

    r = client.post(f"/api/jobs/{job_id}/retry")
    assert r.status_code == 409


def test_retry_not_found(client):
    r = client.post("/api/jobs/nonexistent-job-id/retry")
    assert r.status_code == 404


def test_cancel_running_job(client):
    """Cancel a queued job."""
    r = client.post("/api/jobs/quick", json={
        "urls": ["https://youtube.com/watch?v=cancel_me"],
        "template_id": "viral_reel",
        "aspect_ratio": "9:16",
    })
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    r = client.delete(f"/api/jobs/{job_id}")
    assert r.status_code == 200
    assert r.json()["cancelled"] is True


def test_cancel_done_job(client):
    """Cannot cancel a completed job."""
    import uuid
    import json
    from kairos.database import SessionLocal
    from kairos.models import QuickJob
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    job = QuickJob(
        job_id=str(uuid.uuid4()),
        urls=json.dumps(["https://youtube.com/watch?v=done"]),
        template_id="viral_reel",
        aspect_ratio="9:16",
        job_status="done",
        stage_label="Complete",
        progress=100,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    job_id = job.job_id
    db.close()

    r = client.delete(f"/api/jobs/{job_id}")
    assert r.status_code == 409


def test_download_not_done(client, sample_quick_job):
    """Download returns 404 when job is not done."""
    r = client.get(f"/api/jobs/{sample_quick_job}/download")
    assert r.status_code == 404


def test_download_not_found(client):
    r = client.get("/api/jobs/nonexistent-job-id/download")
    assert r.status_code == 404
