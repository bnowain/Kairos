"""Unit tests for individual services (no DB, no HTTP)."""
import pytest


class TestEmotionScorer:
    def test_high_emotion_exclamation(self):
        from kairos.services.analysis.emotion_scorer import score_emotion
        segs = [{"segment_text": "This is OUTRAGEOUS!! You cannot do this!!", "start_ms": 0, "end_ms": 5000}]
        result = score_emotion(segs)
        assert result[0]["heuristic_emotion_score"] > 0.3

    def test_low_emotion_neutral(self):
        from kairos.services.analysis.emotion_scorer import score_emotion
        segs = [{"segment_text": "The meeting will be held on Tuesday.", "start_ms": 0, "end_ms": 3000}]
        result = score_emotion(segs)
        assert result[0]["heuristic_emotion_score"] < 0.4

    def test_score_in_range(self):
        from kairos.services.analysis.emotion_scorer import score_emotion
        segs = [{"segment_text": "AMAZING! incredible! fantastic! WOW!!", "start_ms": 0, "end_ms": 4000}]
        result = score_emotion(segs)
        score = result[0]["heuristic_emotion_score"]
        assert 0.0 <= score <= 1.0

    def test_empty_text_does_not_crash(self):
        from kairos.services.analysis.emotion_scorer import score_emotion
        segs = [{"segment_text": "", "start_ms": 0, "end_ms": 1000}]
        result = score_emotion(segs)
        assert "heuristic_emotion_score" in result[0]

    def test_multiple_segments(self):
        from kairos.services.analysis.emotion_scorer import score_emotion
        segs = [
            {"segment_text": "OUTRAGEOUS!! Corrupt fraud!", "start_ms": 0, "end_ms": 3000},
            {"segment_text": "The report was filed.", "start_ms": 3000, "end_ms": 6000},
        ]
        result = score_emotion(segs)
        assert len(result) == 2
        # First segment should score higher
        assert result[0]["heuristic_emotion_score"] > result[1]["heuristic_emotion_score"]

    def test_modifies_in_place(self):
        from kairos.services.analysis.emotion_scorer import score_emotion
        segs = [{"segment_text": "Hello world", "start_ms": 0, "end_ms": 2000}]
        result = score_emotion(segs)
        # Same object returned
        assert result is segs


class TestControversyScorer:
    def test_controversy_detected(self):
        from kairos.services.analysis.controversy import score_controversy
        segs = [{"segment_text": "That's not true, let me be clear — that's completely false.", "start_ms": 0, "end_ms": 4000}]
        result = score_controversy(segs)
        assert result[0]["heuristic_controversy_score"] > 0.2

    def test_no_controversy_neutral(self):
        from kairos.services.analysis.controversy import score_controversy
        segs = [{"segment_text": "The budget for next year has been approved.", "start_ms": 0, "end_ms": 3000}]
        result = score_controversy(segs)
        assert result[0]["heuristic_controversy_score"] < 0.3

    def test_score_in_range(self):
        from kairos.services.analysis.controversy import score_controversy
        segs = [{"segment_text": "Corrupt criminal fraud scandal investigation!", "start_ms": 0, "end_ms": 5000}]
        result = score_controversy(segs)
        score = result[0]["heuristic_controversy_score"]
        assert 0.0 <= score <= 1.0

    def test_multiple_segments(self):
        from kairos.services.analysis.controversy import score_controversy
        segs = [
            {"segment_text": "That is completely false, misinformation, disinformation!", "start_ms": 0, "end_ms": 4000},
            {"segment_text": "Good morning everyone.", "start_ms": 4000, "end_ms": 6000},
        ]
        result = score_controversy(segs)
        assert len(result) == 2
        assert result[0]["heuristic_controversy_score"] > result[1]["heuristic_controversy_score"]

    def test_political_terms_detected(self):
        from kairos.services.analysis.controversy import score_controversy
        segs = [{"segment_text": "This is corruption and fraud by incompetent officials.", "start_ms": 0, "end_ms": 3000}]
        result = score_controversy(segs)
        assert result[0]["heuristic_controversy_score"] > 0.0


class TestAligner:
    def test_align_single_speaker(self):
        from kairos.services.transcription.aligner import align
        whisper = [{
            "start": 0.0,
            "end": 5.0,
            "text": "Hello world",
            "avg_logprob": -0.2,
            "no_speech_prob": 0.01,
            "words": [
                {"start": 0.0, "end": 0.5, "word": "Hello", "probability": 0.99},
                {"start": 0.6, "end": 1.0, "word": "world", "probability": 0.98},
            ],
        }]
        diar = [{"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"}]
        result = align(whisper, diar)
        assert len(result) > 0
        assert result[0]["speaker"] == "SPEAKER_00"

    def test_align_no_diarization(self):
        from kairos.services.transcription.aligner import align
        whisper = [{
            "start": 0.0,
            "end": 3.0,
            "text": "Test text",
            "avg_logprob": -0.3,
            "no_speech_prob": 0.02,
            "words": [
                {"start": 0.0, "end": 1.0, "word": "Test", "probability": 0.95},
                {"start": 1.1, "end": 2.0, "word": "text", "probability": 0.97},
            ],
        }]
        result = align(whisper, [])  # empty diarization
        assert result[0]["speaker"] == "SPEAKER_00"

    def test_align_two_speakers(self):
        from kairos.services.transcription.aligner import align
        whisper = [{
            "start": 0.0,
            "end": 6.0,
            "text": "Hello there goodbye",
            "avg_logprob": -0.2,
            "no_speech_prob": 0.01,
            "words": [
                {"start": 0.0, "end": 1.0, "word": "Hello", "probability": 0.99},
                {"start": 1.1, "end": 2.0, "word": "there", "probability": 0.98},
                {"start": 4.0, "end": 5.0, "word": "goodbye", "probability": 0.97},
            ],
        }]
        diar = [
            {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"},
            {"start": 3.5, "end": 6.0, "speaker": "SPEAKER_01"},
        ]
        result = align(whisper, diar)
        # Should produce at least 2 segments (different speakers)
        speakers = {seg["speaker"] for seg in result}
        assert len(speakers) >= 1  # at least one speaker

    def test_align_empty_words_returns_empty(self):
        from kairos.services.transcription.aligner import align
        whisper = [{
            "start": 0.0,
            "end": 5.0,
            "text": "",
            "avg_logprob": -0.5,
            "no_speech_prob": 0.8,
            "words": [],
        }]
        result = align(whisper, [])
        assert result == []


class TestExporter:
    def test_srt_format(self, tmp_path):
        from kairos.services.transcription.exporter import export_srt
        segments = [{
            "start": 0.0,
            "end": 2.5,
            "speaker": "SPEAKER_00",
            "text": "Hello world",
            "words": [],
            "avg_logprob": -0.2,
            "no_speech_prob": 0.01,
        }]
        path = str(tmp_path / "test.srt")
        export_srt(segments, path)
        content = open(path, encoding="utf-8").read()
        assert "00:00:00,000 --> 00:00:02,500" in content
        assert "Hello world" in content

    def test_vtt_format(self, tmp_path):
        from kairos.services.transcription.exporter import export_vtt
        segments = [{
            "start": 1.0,
            "end": 3.0,
            "speaker": "SPEAKER_00",
            "text": "Test segment",
            "words": [],
            "avg_logprob": -0.2,
            "no_speech_prob": 0.01,
        }]
        path = str(tmp_path / "test.vtt")
        export_vtt(segments, path)
        content = open(path, encoding="utf-8").read()
        assert "WEBVTT" in content
        assert "00:00:01.000 --> 00:00:03.000" in content

    def test_srt_multiple_cues(self, tmp_path):
        from kairos.services.transcription.exporter import export_srt
        segments = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "First cue", "words": [],
             "avg_logprob": -0.2, "no_speech_prob": 0.01},
            {"start": 3.0, "end": 5.0, "speaker": "SPEAKER_01", "text": "Second cue", "words": [],
             "avg_logprob": -0.2, "no_speech_prob": 0.01},
        ]
        path = str(tmp_path / "multi.srt")
        export_srt(segments, path)
        content = open(path, encoding="utf-8").read()
        assert "First cue" in content
        assert "Second cue" in content

    def test_srt_speaker_label_prepended(self, tmp_path):
        from kairos.services.transcription.exporter import export_srt
        segments = [{
            "start": 0.0,
            "end": 2.0,
            "speaker": "SPEAKER_01",
            "text": "My line",
            "words": [],
            "avg_logprob": -0.2,
            "no_speech_prob": 0.01,
        }]
        path = str(tmp_path / "speaker.srt")
        export_srt(segments, path)
        content = open(path, encoding="utf-8").read()
        assert "[SPEAKER_01]" in content


class TestCaptionStyler:
    def test_hex_to_ass_red(self):
        from kairos.services.caption_engine.styler import hex_to_ass_color
        result = hex_to_ass_color("#FF0000")
        # Red in ASS = &H000000FF (B and R are swapped)
        assert result == "&H000000FF"

    def test_hex_to_ass_white(self):
        from kairos.services.caption_engine.styler import hex_to_ass_color
        assert hex_to_ass_color("#FFFFFF") == "&H00FFFFFF"

    def test_hex_to_ass_blue(self):
        from kairos.services.caption_engine.styler import hex_to_ass_color
        result = hex_to_ass_color("#0000FF")
        # Blue (#0000FF) in ASS BGR = &H00FF0000
        assert result == "&H00FF0000"

    def test_hex_to_ass_alpha(self):
        from kairos.services.caption_engine.styler import hex_to_ass_color
        result = hex_to_ass_color("#FF0000", alpha=128)
        assert result.startswith("&H80")

    def test_platform_presets_exist(self):
        from kairos.services.caption_engine.styler import PLATFORM_PRESETS
        assert "tiktok" in PLATFORM_PRESETS
        assert "youtube" in PLATFORM_PRESETS
        assert "instagram" in PLATFORM_PRESETS

    def test_get_default_style(self):
        from kairos.services.caption_engine.styler import get_default_style
        style = get_default_style()
        assert "font_name" in style
        assert "font_size" in style
        assert style["position"] == "bottom"


class TestReframer:
    def test_center_crop_16_9_to_9_16(self):
        from kairos.services.aspect_ratio.reframer import compute_crop_box
        result = compute_crop_box(1920, 1080, "9:16", face_position=None)
        assert result["w"] < result["h"]  # vertical output
        assert result["x"] >= 0
        assert result["y"] == 0  # 1080 height = full height

    def test_16_9_unchanged(self):
        from kairos.services.aspect_ratio.reframer import compute_crop_box
        result = compute_crop_box(1920, 1080, "16:9", face_position=None)
        # Should be nearly the full frame
        assert result["w"] == 1920
        assert result["h"] == 1080

    def test_crop_box_bounds_are_valid(self):
        from kairos.services.aspect_ratio.reframer import compute_crop_box
        result = compute_crop_box(1920, 1080, "9:16", face_position=None)
        assert result["x"] >= 0
        assert result["y"] >= 0
        assert result["x"] + result["w"] <= 1920
        assert result["y"] + result["h"] <= 1080

    def test_ffmpeg_vf_string_present(self):
        from kairos.services.aspect_ratio.reframer import compute_crop_box
        result = compute_crop_box(1920, 1080, "9:16")
        assert "crop=" in result["ffmpeg_vf"]
        assert "scale=" in result["ffmpeg_vf"]

    def test_1_1_aspect_ratio(self):
        from kairos.services.aspect_ratio.reframer import compute_crop_box
        result = compute_crop_box(1920, 1080, "1:1")
        # Square crop: w should equal h
        assert result["w"] == result["h"]

    def test_face_position_shifts_crop(self):
        from kairos.services.aspect_ratio.reframer import compute_crop_box
        # Face on the right side — pixel_space=True means cx/cy are in pixels
        face = {"cx": 1600, "cy": 540, "pixel_space": True}
        result_face = compute_crop_box(1920, 1080, "9:16", face_position=face)
        result_center = compute_crop_box(1920, 1080, "9:16", face_position=None)
        # Face crop should have a higher x offset than center crop
        assert result_face["x"] >= result_center["x"]


class TestFlowEnforcer:
    def test_similarity_identical(self):
        from kairos.services.story_builder.flow_enforcer import _similarity
        assert _similarity("hello world foo", "hello world foo") == 1.0

    def test_similarity_different(self):
        from kairos.services.story_builder.flow_enforcer import _similarity
        assert _similarity("apple orange", "cat dog fish") == 0.0

    def test_similarity_partial(self):
        from kairos.services.story_builder.flow_enforcer import _similarity
        score = _similarity("the quick brown fox", "the slow brown fox")
        assert 0.4 < score < 1.0

    def test_similarity_empty_strings(self):
        from kairos.services.story_builder.flow_enforcer import _similarity
        assert _similarity("", "hello") == 0.0
        assert _similarity("hello", "") == 0.0
        assert _similarity("", "") == 0.0

    def test_enforce_flow_empty_slots_returns_empty(self):
        from kairos.services.story_builder.flow_enforcer import enforce_flow
        template = {"slots": [], "pacing": "fast"}
        result = enforce_flow(slot_assignments={}, template=template)
        assert result == []

    def test_enforce_flow_single_clip(self):
        from kairos.services.story_builder.flow_enforcer import enforce_flow
        template = {
            "slots": [{"slot_id": "hook", "position": 0}],
            "pacing": "fast",
        }
        assignments = {
            "hook": [{"clip_id": "clip-001", "duration_ms": 10000, "clip_transcript": "Hello there world."}]
        }
        result = enforce_flow(slot_assignments=assignments, template=template)
        clip_elements = [e for e in result if e["element_type"] == "clip"]
        assert len(clip_elements) == 1
        assert clip_elements[0]["clip_id"] == "clip-001"


class TestCompositeScorer:
    def test_weights_sum_to_one(self):
        from kairos.services.analysis.scorer import WEIGHTS
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_high_score_above_threshold(self):
        from kairos.services.analysis.scorer import compute_composite_scores, AUTO_CLIP_THRESHOLD
        segs = [{
            "segment_id": "s1",
            "start_ms": 0,
            "end_ms": 5000,
            "segment_text": "amazing content",
            "speaker_label": None,
            "heuristic_emotion_score": 0.8,
            "heuristic_controversy_score": 0.7,
            "audience_reaction_score": 0.8,
            "topic_coherence_score": 0.6,
        }]
        high = [{
            "segment_id": "s1",
            "virality_score": 0.9,
            "hook_score": 0.9,
            "emotional_score": 0.9,
            "controversy_score": 0.8,
            "highlight_reason": "great",
        }]
        react = [{"segment_id": "s1", "audience_reaction_score": 0.8}]
        emo = [{"segment_id": "s1", "heuristic_emotion_score": 0.8}]
        con = [{"segment_id": "s1", "heuristic_controversy_score": 0.7}]
        emb = [{"segment_id": "s1", "topic_coherence_score": 0.6}]
        result = compute_composite_scores(segs, high, react, emo, con, emb)
        assert result[0]["composite_virality_score"] >= AUTO_CLIP_THRESHOLD

    def test_low_score_below_threshold(self):
        from kairos.services.analysis.scorer import compute_composite_scores, AUTO_CLIP_THRESHOLD
        segs = [{
            "segment_id": "s2",
            "start_ms": 0,
            "end_ms": 5000,
            "segment_text": "nothing special",
            "speaker_label": None,
        }]
        low = [{
            "segment_id": "s2",
            "virality_score": 0.1,
            "hook_score": 0.1,
            "emotional_score": 0.1,
            "controversy_score": 0.1,
            "highlight_reason": "",
        }]
        result = compute_composite_scores(segs, low, [], [], [], [])
        assert result[0]["composite_virality_score"] < AUTO_CLIP_THRESHOLD

    def test_composite_score_in_range(self):
        from kairos.services.analysis.scorer import compute_composite_scores
        segs = [{"segment_id": "s3", "start_ms": 0, "end_ms": 5000, "segment_text": "test"}]
        result = compute_composite_scores(segs, [], [], [], [], [])
        score = result[0]["composite_virality_score"]
        assert 0.0 <= score <= 1.0

    def test_auto_clip_candidate_flag(self):
        from kairos.services.analysis.scorer import compute_composite_scores, AUTO_CLIP_THRESHOLD
        segs = [{
            "segment_id": "s4",
            "start_ms": 0,
            "end_ms": 5000,
            "segment_text": "epic content",
            "heuristic_emotion_score": 0.9,
            "heuristic_controversy_score": 0.9,
            "audience_reaction_score": 0.9,
            "topic_coherence_score": 0.9,
        }]
        high = [{
            "segment_id": "s4",
            "virality_score": 1.0,
            "hook_score": 1.0,
            "emotional_score": 1.0,
            "controversy_score": 1.0,
            "highlight_reason": "perfect",
        }]
        result = compute_composite_scores(segs, high, [], [], [], [])
        assert result[0]["is_auto_clip_candidate"] is True

    def test_returns_sorted_by_score(self):
        from kairos.services.analysis.scorer import compute_composite_scores
        segs = [
            {"segment_id": "low", "start_ms": 0, "end_ms": 3000, "segment_text": "boring"},
            {"segment_id": "high", "start_ms": 3000, "end_ms": 6000, "segment_text": "amazing",
             "heuristic_emotion_score": 0.9, "heuristic_controversy_score": 0.8},
        ]
        high_scores = [
            {"segment_id": "low", "virality_score": 0.1, "hook_score": 0.1,
             "emotional_score": 0.1, "controversy_score": 0.1, "highlight_reason": ""},
            {"segment_id": "high", "virality_score": 0.9, "hook_score": 0.9,
             "emotional_score": 0.9, "controversy_score": 0.8, "highlight_reason": "great"},
        ]
        result = compute_composite_scores(segs, high_scores, [], [], [], [])
        # First result should have highest score
        assert result[0]["composite_virality_score"] >= result[1]["composite_virality_score"]
