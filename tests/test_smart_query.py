"""Tests for /api/smart-query and /api/intent-profiles endpoints."""


# ── Smart Query CRUD ─────────────────────────────────────────────────────────


def test_create_smart_query(client):
    r = client.post("/api/smart-query", json={
        "query_text": "Find heated debate moments",
        "query_source": "kairos",
        "scorer_models": ["default"],
    })
    assert r.status_code == 202
    data = r.json()
    assert data["query_text"] == "Find heated debate moments"
    assert data["query_status"] == "pending"
    assert "query_id" in data


def test_list_smart_queries(client, sample_smart_query):
    r = client.get("/api/smart-query")
    assert r.status_code == 200
    queries = r.json()
    assert isinstance(queries, list)
    assert any(q["query_id"] == sample_smart_query[0] for q in queries)


def test_get_smart_query(client, sample_smart_query):
    query_id = sample_smart_query[0]
    r = client.get(f"/api/smart-query/{query_id}")
    assert r.status_code == 200
    assert r.json()["query_id"] == query_id
    assert r.json()["query_status"] == "done"


def test_get_smart_query_not_found(client):
    r = client.get("/api/smart-query/nonexistent-query-id")
    assert r.status_code == 404


def test_get_smart_query_results_empty(client):
    """Create a query with no candidates — results should be empty."""
    r = client.post("/api/smart-query", json={
        "query_text": "No results expected",
        "query_source": "kairos",
    })
    assert r.status_code == 202
    qid = r.json()["query_id"]
    r = client.get(f"/api/smart-query/{qid}/results")
    assert r.status_code == 200
    assert r.json() == []


def test_get_smart_query_results(client, sample_smart_query):
    query_id = sample_smart_query[0]
    r = client.get(f"/api/smart-query/{query_id}/results")
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    assert len(results) >= 1
    assert results[0]["candidate_text"] == "This is a heated exchange about policy."


# ── Candidate feedback ───────────────────────────────────────────────────────


def test_rate_candidate_thumbs_up(client, sample_smart_query):
    candidate_id = sample_smart_query[1]
    r = client.post(f"/api/smart-query/candidates/{candidate_id}/rate", json={
        "rating": 1,
        "save_as_example": False,
    })
    assert r.status_code == 200
    assert r.json()["candidate_user_rating"] == 1


def test_rate_candidate_thumbs_down(client, sample_smart_query):
    candidate_id = sample_smart_query[1]
    r = client.post(f"/api/smart-query/candidates/{candidate_id}/rate", json={
        "rating": -1,
        "note": "Not relevant",
        "save_as_example": False,
    })
    assert r.status_code == 200
    assert r.json()["candidate_user_rating"] == -1


def test_rate_candidate_not_found(client):
    r = client.post("/api/smart-query/candidates/nonexistent-id/rate", json={
        "rating": 1,
    })
    assert r.status_code == 404


def test_import_candidate_as_clip(client, sample_smart_query):
    candidate_id = sample_smart_query[1]
    r = client.post(f"/api/smart-query/candidates/{candidate_id}/import")
    assert r.status_code == 200
    data = r.json()
    assert "clip_id" in data
    assert data["already_imported"] is False


def test_import_candidate_idempotent(client, sample_smart_query):
    candidate_id = sample_smart_query[1]
    # First import
    client.post(f"/api/smart-query/candidates/{candidate_id}/import")
    # Second import should return already_imported
    r = client.post(f"/api/smart-query/candidates/{candidate_id}/import")
    assert r.status_code == 200
    assert r.json()["already_imported"] is True


def test_import_candidate_not_found(client):
    r = client.post("/api/smart-query/candidates/nonexistent-id/import")
    assert r.status_code == 404


# ── Intent Profiles ──────────────────────────────────────────────────────────


def test_list_intent_profiles(client):
    r = client.get("/api/intent-profiles")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_intent_profile(client):
    r = client.post("/api/intent-profiles", json={
        "intent_name": "Combative Moments Test",
        "intent_description": "Find heated debates",
        "intent_system_prompt": "Score for conflict level",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["intent_name"] == "Combative Moments Test"
    assert "intent_profile_id" in data


def test_create_intent_profile_duplicate_name(client):
    name = "Duplicate Intent Test Unique"
    client.post("/api/intent-profiles", json={"intent_name": name})
    r2 = client.post("/api/intent-profiles", json={"intent_name": name})
    assert r2.status_code == 409


def test_get_intent_profile(client):
    r = client.post("/api/intent-profiles", json={
        "intent_name": "Get Profile Test Unique",
    })
    assert r.status_code == 201
    pid = r.json()["intent_profile_id"]

    r = client.get(f"/api/intent-profiles/{pid}")
    assert r.status_code == 200
    assert r.json()["intent_profile_id"] == pid


def test_get_intent_profile_not_found(client):
    r = client.get("/api/intent-profiles/nonexistent-profile-id")
    assert r.status_code == 404


def test_update_intent_profile(client):
    r = client.post("/api/intent-profiles", json={
        "intent_name": "Update Profile Test Unique",
    })
    assert r.status_code == 201
    pid = r.json()["intent_profile_id"]

    r = client.patch(f"/api/intent-profiles/{pid}", json={
        "intent_name": "Updated Name",
        "intent_description": "New description",
    })
    assert r.status_code == 200
    assert r.json()["intent_name"] == "Updated Name"
    assert r.json()["intent_description"] == "New description"


def test_list_intent_examples(client):
    r = client.post("/api/intent-profiles", json={
        "intent_name": "Examples Profile Test Unique",
    })
    assert r.status_code == 201
    pid = r.json()["intent_profile_id"]

    r = client.get(f"/api/intent-profiles/{pid}/examples")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
