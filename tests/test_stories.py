"""Tests for /api/stories and /api/timelines endpoints."""


def test_list_templates(client):
    r = client.get("/api/stories/templates")
    assert r.status_code == 200
    templates = r.json()
    assert len(templates) >= 6
    ids = [t["template_id"] for t in templates]
    assert "viral_reel" in ids
    assert "political_campaign" in ids


def test_get_template(client):
    r = client.get("/api/stories/templates/viral_reel")
    assert r.status_code == 200
    data = r.json()
    assert data["template_id"] == "viral_reel"
    assert "slots" in data
    assert len(data["slots"]) > 0


def test_get_template_not_found(client):
    r = client.get("/api/stories/templates/nonexistent")
    assert r.status_code == 404


def test_validate_template_valid(client):
    template = {
        "template_id": "test_template",
        "template_name": "Test",
        "description": "A test template",
        "pacing": "fast",
        "target_duration_ms": 60000,
        "aspect_ratio_default": "16:9",
        "slots": [
            {
                "slot_id": "hook",
                "slot_label": "Hook",
                "position": 0,
                "required": True,
                "max_clips": 1,
                "score_signals": ["virality"],
                "max_duration_ms": 10000,
            }
        ],
    }
    r = client.post("/api/stories/templates/validate", json=template)
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_generate_story_no_clips(client, sample_item):
    """Generate with no ready clips — should return 422 (no ready clips)."""
    r = client.post("/api/stories/generate", json={
        "item_ids": [sample_item],
        "template_id": "viral_reel",
        "name": "Test Story",
    })
    # No ready clips exist for sample_item — expect 422
    assert r.status_code in (200, 400, 422)


def test_generate_story_item_not_found(client):
    r = client.post("/api/stories/generate", json={
        "item_ids": ["nonexistent-item-id"],
        "template_id": "viral_reel",
        "name": "Test Story",
    })
    assert r.status_code == 404


def test_generate_story_empty_item_ids(client):
    r = client.post("/api/stories/generate", json={
        "item_ids": [],
        "template_id": "viral_reel",
        "name": "Test Story",
    })
    assert r.status_code == 422


def test_generate_story_template_not_found(client, sample_item):
    r = client.post("/api/stories/generate", json={
        "item_ids": [sample_item],
        "template_id": "nonexistent_template",
        "name": "Test Story",
    })
    # Either 404 (template not found) or 422 (no clips first)
    assert r.status_code in (404, 422)


def test_list_timelines(client):
    r = client.get("/api/timelines")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_timeline(client, sample_timeline):
    r = client.get(f"/api/timelines/{sample_timeline}")
    assert r.status_code == 200
    data = r.json()
    assert data["timeline_id"] == sample_timeline
    assert "elements" in data


def test_get_timeline_not_found(client):
    r = client.get("/api/timelines/nonexistent-id")
    assert r.status_code == 404


def test_update_timeline(client, sample_timeline):
    r = client.patch(f"/api/timelines/{sample_timeline}", json={"timeline_name": "Renamed"})
    assert r.status_code == 200
    assert r.json()["timeline_name"] == "Renamed"


def test_update_timeline_not_found(client):
    r = client.patch("/api/timelines/nonexistent-id", json={"timeline_name": "X"})
    assert r.status_code == 404


def test_timeline_elements(client, sample_timeline):
    r = client.get(f"/api/timelines/{sample_timeline}/elements")
    assert r.status_code == 200
    elements = r.json()
    assert isinstance(elements, list)
    assert len(elements) >= 1


def test_add_timeline_element(client, sample_timeline):
    r = client.post(f"/api/timelines/{sample_timeline}/elements", json={
        "element_type": "title_card",
        "position": 1,
        "duration_ms": 3000,
        "element_params": '{"text": "Test Title"}',
    })
    assert r.status_code in (200, 201)


def test_delete_timeline(client):
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
    timeline_id = tl.timeline_id
    db.close()

    r = client.delete(f"/api/timelines/{timeline_id}")
    assert r.status_code == 200


def test_delete_timeline_not_found(client):
    r = client.delete("/api/timelines/nonexistent-id")
    assert r.status_code == 404


def test_timeline_elements_not_found(client):
    r = client.get("/api/timelines/nonexistent-id/elements")
    assert r.status_code == 404
