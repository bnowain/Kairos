"""
Shared pytest fixtures for Kairos backend tests.
Uses FastAPI TestClient with an isolated SQLite database.
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture(scope="session")
def client(tmp_dir):
    """TestClient with isolated temp database and media dirs."""
    # Point all paths to temp dir before importing app
    os.environ["KAIROS_MEDIA_ROOT"] = tmp_dir
    # Override DATABASE_PATH via env before import
    db_path = os.path.join(tmp_dir, "test_kairos.db")
    os.environ["KAIROS_TEST_DB"] = db_path

    # Patch config before app import
    import kairos.config as cfg
    cfg.DATABASE_PATH = type(cfg.DATABASE_PATH)(db_path)
    cfg.DATABASE_URL = f"sqlite:///{db_path}"
    cfg.MEDIA_LIBRARY_ROOT = type(cfg.MEDIA_LIBRARY_ROOT)(tmp_dir + "/media_library")
    cfg.MEDIA_DIR = type(cfg.MEDIA_DIR)(tmp_dir + "/media")
    cfg.CLIPS_DIR = cfg.MEDIA_DIR / "clips"
    cfg.RENDERS_DIR = cfg.MEDIA_DIR / "renders"
    cfg.PREVIEWS_DIR = cfg.MEDIA_DIR / "previews"
    cfg.AUDIO_DIR = cfg.MEDIA_DIR / "audio"
    cfg.THUMBS_DIR = cfg.MEDIA_DIR / "thumbs"
    for d in [
        cfg.MEDIA_LIBRARY_ROOT,
        cfg.CLIPS_DIR,
        cfg.RENDERS_DIR,
        cfg.PREVIEWS_DIR,
        cfg.AUDIO_DIR,
        cfg.THUMBS_DIR,
        cfg.DATABASE_PATH.parent,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # Re-init database with test path
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    import kairos.database as db_mod
    import kairos.models as models

    test_engine = create_engine(
        cfg.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine, "connect")
    def _pragmas(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    db_mod.engine = test_engine
    db_mod.SessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    models.Base.metadata.create_all(bind=test_engine)

    from kairos.main import app
    from kairos.database import get_db
    # Also import local get_db functions from routers that define their own
    from kairos.routers import clips as clips_router
    from kairos.routers import transcription as transcription_router
    from kairos.routers import analysis as analysis_router

    def override_get_db():
        db = db_mod.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[clips_router.get_db] = override_get_db
    app.dependency_overrides[transcription_router._get_db] = override_get_db
    app.dependency_overrides[analysis_router._get_db] = override_get_db

    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_item(client):
    """Create a MediaItem directly in DB and return its item_id."""
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import MediaItem
    from datetime import datetime

    db = SessionLocal()
    item = MediaItem(
        item_id=str(uuid.uuid4()),
        platform="youtube",
        platform_video_id="test_vid_001",
        item_title="Test Video",
        item_channel="Test Channel",
        duration_seconds=120.0,
        original_url="https://youtube.com/watch?v=test_vid_001",
        item_status="ready",
        has_captions=0,
        created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    item_id = item.item_id
    db.close()
    return item_id


@pytest.fixture
def sample_clip(client, sample_item):
    """Create a ready Clip row and return its clip_id."""
    import uuid
    from kairos.database import SessionLocal
    from kairos.models import Clip
    from datetime import datetime

    db = SessionLocal()
    clip = Clip(
        clip_id=str(uuid.uuid4()),
        item_id=sample_item,
        start_ms=5000,
        end_ms=20000,
        duration_ms=15000,
        virality_score=0.75,
        clip_status="ready",
        clip_source="ai",
        clip_transcript="This is a test clip transcript.",
        created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)
    clip_id = clip.clip_id
    db.close()
    return clip_id


@pytest.fixture
def sample_timeline(client, sample_clip):
    """Create a timeline with one clip element."""
    import uuid
    import json
    from kairos.database import SessionLocal
    from kairos.models import Timeline, TimelineElement
    from datetime import datetime

    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    tl = Timeline(
        timeline_id=str(uuid.uuid4()),
        timeline_name="Test Timeline",
        story_template="viral_reel",
        aspect_ratio="16:9",
        target_duration_ms=15000,
        timeline_status="ready",
        created_at=now,
        updated_at=now,
    )
    db.add(tl)
    db.commit()
    el = TimelineElement(
        element_id=str(uuid.uuid4()),
        timeline_id=tl.timeline_id,
        element_type="clip",
        position=0,
        start_ms=0,
        duration_ms=15000,
        clip_id=sample_clip,
        element_params=json.dumps({}),
        created_at=now,
    )
    db.add(el)
    db.commit()
    timeline_id = tl.timeline_id
    db.close()
    return timeline_id
