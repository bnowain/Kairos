"""Tests for /api/timelines endpoints."""

import json


# ── Timeline CRUD ────────────────────────────────────────────────────────────


def test_list_timelines(client, sample_timeline):
    r = client.get("/api/timelines")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert any(t["timeline_id"] == sample_timeline for t in r.json())


def test_list_timelines_filter_status(client, sample_timeline):
    r = client.get("/api/timelines?status=ready")
    assert r.status_code == 200
    timelines = r.json()
    assert all(t["timeline_status"] == "ready" for t in timelines)


def test_get_timeline_detail(client, sample_timeline):
    r = client.get(f"/api/timelines/{sample_timeline}")
    assert r.status_code == 200
    data = r.json()
    assert data["timeline_id"] == sample_timeline
    assert data["timeline_name"] == "Test Timeline"
    assert "elements" in data
    assert len(data["elements"]) >= 1


def test_patch_timeline_name(client, sample_timeline):
    r = client.patch(f"/api/timelines/{sample_timeline}", json={
        "timeline_name": "Renamed Timeline",
    })
    assert r.status_code == 200
    assert r.json()["timeline_name"] == "Renamed Timeline"


def test_patch_timeline_aspect_ratio(client, sample_timeline):
    r = client.patch(f"/api/timelines/{sample_timeline}", json={
        "aspect_ratio": "9:16",
    })
    assert r.status_code == 200
    assert r.json()["aspect_ratio"] == "9:16"


def test_patch_timeline_not_found(client):
    r = client.patch("/api/timelines/nonexistent-id", json={"timeline_name": "X"})
    assert r.status_code == 404


def test_delete_timeline(client, sample_clip):
    """Create a separate timeline for deletion to avoid breaking other tests."""
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import Timeline
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    tl = Timeline(
        timeline_id=str(uuid.uuid4()),
        timeline_name="Delete Me",
        aspect_ratio="16:9",
        timeline_status="draft",
        created_at=now,
        updated_at=now,
    )
    db.add(tl)
    db.commit()
    tid = tl.timeline_id
    db.close()

    r = client.delete(f"/api/timelines/{tid}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    # Verify deleted
    r = client.get(f"/api/timelines/{tid}")
    assert r.status_code == 404


# ── Element CRUD ─────────────────────────────────────────────────────────────


def test_list_elements_ordered(client, sample_timeline):
    r = client.get(f"/api/timelines/{sample_timeline}/elements")
    assert r.status_code == 200
    elements = r.json()
    assert isinstance(elements, list)
    assert len(elements) >= 1
    # Verify ordered by position
    positions = [e["position"] for e in elements]
    assert positions == sorted(positions)


def test_add_element_at_end(client, sample_timeline):
    r = client.post(f"/api/timelines/{sample_timeline}/elements", json={
        "element_type": "title_card",
        "position": 99,
        "duration_ms": 3000,
        "element_params": json.dumps({"text": "Hello World"}),
    })
    assert r.status_code == 201
    data = r.json()
    assert data["element_type"] == "title_card"
    assert data["duration_ms"] == 3000


def test_add_element_at_position_zero(client, sample_timeline):
    r = client.post(f"/api/timelines/{sample_timeline}/elements", json={
        "element_type": "title_card",
        "position": 0,
        "duration_ms": 2000,
    })
    assert r.status_code == 201
    assert r.json()["position"] == 0

    # Verify original element was shifted
    r = client.get(f"/api/timelines/{sample_timeline}/elements")
    elements = r.json()
    positions = [e["position"] for e in elements]
    assert positions == sorted(positions)


def test_add_element_to_nonexistent_timeline(client):
    r = client.post("/api/timelines/nonexistent-id/elements", json={
        "element_type": "clip",
        "position": 0,
        "duration_ms": 5000,
    })
    assert r.status_code == 404


def test_patch_element_params(client, sample_timeline):
    r = client.get(f"/api/timelines/{sample_timeline}/elements")
    eid = r.json()[0]["element_id"]

    r = client.patch(f"/api/timelines/{sample_timeline}/elements/{eid}", json={
        "element_params": json.dumps({"volume": 0.8}),
    })
    assert r.status_code == 200


def test_patch_element_duration(client, sample_timeline):
    r = client.get(f"/api/timelines/{sample_timeline}/elements")
    eid = r.json()[0]["element_id"]

    r = client.patch(f"/api/timelines/{sample_timeline}/elements/{eid}", json={
        "duration_ms": 10000,
    })
    assert r.status_code == 200
    assert r.json()["duration_ms"] == 10000


def test_patch_element_not_found(client, sample_timeline):
    r = client.patch(f"/api/timelines/{sample_timeline}/elements/nonexistent-eid", json={
        "duration_ms": 5000,
    })
    assert r.status_code == 404


def test_delete_element(client, sample_timeline, sample_clip):
    """Add an element then delete it."""
    r = client.post(f"/api/timelines/{sample_timeline}/elements", json={
        "element_type": "title_card",
        "position": 99,
        "duration_ms": 1000,
    })
    assert r.status_code == 201
    eid = r.json()["element_id"]

    r = client.delete(f"/api/timelines/{sample_timeline}/elements/{eid}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_delete_element_not_found(client, sample_timeline):
    r = client.delete(f"/api/timelines/{sample_timeline}/elements/nonexistent-eid")
    assert r.status_code == 404


def test_reorder_elements(client, sample_timeline):
    # Get current elements
    r = client.get(f"/api/timelines/{sample_timeline}/elements")
    elements = r.json()
    if len(elements) < 2:
        # Add a second element so we can reorder
        client.post(f"/api/timelines/{sample_timeline}/elements", json={
            "element_type": "title_card",
            "position": 99,
            "duration_ms": 2000,
        })
        r = client.get(f"/api/timelines/{sample_timeline}/elements")
        elements = r.json()

    ids = [e["element_id"] for e in elements]
    reversed_ids = list(reversed(ids))

    r = client.post(f"/api/timelines/{sample_timeline}/reorder", json={
        "element_ids": reversed_ids,
    })
    assert r.status_code == 200
    result = r.json()
    result_ids = [e["element_id"] for e in result]
    assert result_ids == reversed_ids
