"""Tests for /api/health and /api/config."""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "cuda_available" in data
    assert "nvenc_available" in data


def test_config(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    assert "whisper_model" in data
    assert "ollama_host" in data


def test_jobs(client):
    r = client.get("/api/jobs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
