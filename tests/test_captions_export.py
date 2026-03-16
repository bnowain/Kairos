"""Tests for caption export and timeline caption generation endpoints."""


def _create_style(client, name):
    """Helper to create a caption style and return its style_id."""
    r = client.post("/api/captions/styles", json={
        "style_name": name,
        "font_name": "Impact",
        "font_size": 64,
        "font_color": "#FFFF00",
        "outline_color": "#000000",
        "outline_width": 3,
        "shadow": 0,
        "position": "bottom",
    })
    assert r.status_code in (200, 201)
    return r.json()["style_id"]


# ── Clip caption export ──────────────────────────────────────────────────────


def test_export_clip_captions_srt(client, sample_clip):
    r = client.post(f"/api/captions/clips/{sample_clip}/export?fmt=srt")
    # May succeed or return empty content depending on transcript data
    assert r.status_code == 200


def test_export_clip_captions_vtt(client, sample_clip):
    r = client.post(f"/api/captions/clips/{sample_clip}/export?fmt=vtt")
    assert r.status_code == 200


def test_export_clip_captions_ass(client, sample_clip):
    r = client.post(f"/api/captions/clips/{sample_clip}/export?fmt=ass")
    assert r.status_code == 200


def test_export_clip_invalid_format(client, sample_clip):
    r = client.post(f"/api/captions/clips/{sample_clip}/export?fmt=json")
    assert r.status_code == 422


def test_export_clip_not_found(client):
    r = client.post("/api/captions/clips/nonexistent-clip-id/export?fmt=srt")
    assert r.status_code == 404


def test_export_clip_with_style(client, sample_clip):
    style_id = _create_style(client, "Export Style Test Unique 001")
    r = client.post(f"/api/captions/clips/{sample_clip}/export?fmt=srt&style_id={style_id}")
    assert r.status_code == 200


def test_export_clip_bad_style(client, sample_clip):
    r = client.post(f"/api/captions/clips/{sample_clip}/export?fmt=srt&style_id=nonexistent-style")
    assert r.status_code == 404


# ── Timeline caption generation ──────────────────────────────────────────────


def test_generate_timeline_captions(client, sample_timeline):
    r = client.post(f"/api/captions/timeline/{sample_timeline}/generate")
    assert r.status_code == 200
    data = r.json()
    assert "ass_path" in data
    assert "cue_count" in data


def test_generate_timeline_captions_not_found(client):
    r = client.post("/api/captions/timeline/nonexistent-timeline-id/generate")
    assert r.status_code == 404


def test_generate_timeline_captions_with_style(client, sample_timeline):
    style_id = _create_style(client, "Timeline Style Test Unique 002")
    r = client.post(
        f"/api/captions/timeline/{sample_timeline}/generate",
        json={"style_id": style_id},
    )
    assert r.status_code == 200
    assert "ass_path" in r.json()
