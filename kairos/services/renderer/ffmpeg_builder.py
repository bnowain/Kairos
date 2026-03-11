"""
Build FFmpeg filter_complex commands from a TimelineModel.

A timeline is a sequence of: clip | transition | title_card | overlay | audio_track elements.
This module converts that into an ffmpeg command that can be run as a subprocess.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Output resolution map for each quality level
_RESOLUTIONS = {
    "16:9": {"final": (1920, 1080), "preview": (1280, 720)},
    "9:16": {"final": (1080, 1920), "preview": (720, 1280)},
    "1:1":  {"final": (1080, 1080), "preview": (720, 720)},
}


def _get_resolution(aspect_ratio: str, quality: str) -> tuple[int, int]:
    """Return (width, height) for the given aspect ratio and quality."""
    ratio_map = _RESOLUTIONS.get(aspect_ratio, _RESOLUTIONS["16:9"])
    q = quality if quality in ("preview", "final") else "final"
    return ratio_map[q]


def _parse_params(element: dict) -> dict:
    """Parse element_params JSON, return {} on failure."""
    raw = element.get("element_params")
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _ms_to_sec(ms: int) -> float:
    return ms / 1000.0


def build_concat_filter(
    clip_paths: list[str],
    transitions: list[dict],
    output_resolution: tuple[int, int],
    crop_params: dict = None,
) -> tuple[str, str]:
    """
    Build the filter_complex string for concatenating clips with transitions.
    Returns (filter_complex_str, output_stream_label).

    For cut transitions: use simple concat filter.
    For fade transitions: use xfade filter between adjacent clip pairs.
    For wipe transitions: use xfade=effect=wipeleft (or wiperight).
    """
    if not clip_paths:
        return "", "[v_out]"

    W, H = output_resolution
    n = len(clip_paths)
    parts: list[str] = []

    # Build a map of position → transition (keyed by which clip index it follows)
    # transitions list: dicts with {position: int, params: {type: str, duration_ms: int}}
    trans_map: dict[int, dict] = {}
    for t in transitions:
        pos = t.get("position", 0)
        trans_map[pos] = _parse_params(t) if isinstance(t.get("element_params"), str) else t.get("params", {})

    # Scale + crop each input to output resolution
    for i in range(n):
        if crop_params and i < len(list(crop_params.keys())):
            # If clip_id-keyed crop_params — handled outside; just scale here
            pass
        parts.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                     f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2[v{i}]")

    if n == 1:
        # Single clip: just use scaled output
        parts.append(f"[v0]null[v_out]")
        return ";\n".join(parts), "[v_out]"

    # Check if any transitions are non-cut
    has_xfade = any(
        trans_map.get(i, {}).get("type", "cut") not in ("cut", "")
        for i in range(n - 1)
    )

    if not has_xfade:
        # Simple concat
        inputs = "".join(f"[v{i}][{i}:a]" for i in range(n))
        parts.append(f"{inputs}concat=n={n}:v=1:a=1[v_out][a_out]")
        return ";\n".join(parts), "[v_out]"

    # xfade between pairs
    current_label = "v0"
    for i in range(n - 1):
        t_info = trans_map.get(i, {})
        t_type = t_info.get("type", "cut")
        dur = _ms_to_sec(int(t_info.get("duration_ms", 500)))

        # offset = sum of durations of clips 0..i minus half the transition duration
        # We approximate offset as sum of clip durations up to clip i
        # (caller is expected to pass element start_ms for precision; here we do best-effort)
        offset = 0.0  # simplified — actual offset computed from timeline element start_ms

        if t_type == "fade":
            effect = "fade"
        elif t_type in ("wipe", "wipe_left"):
            effect = "wipeleft"
        elif t_type == "wipe_right":
            effect = "wiperight"
        else:
            effect = "fade"

        out_label = f"xf{i}" if i < n - 2 else "v_out"
        parts.append(
            f"[{current_label}][v{i + 1}]xfade=transition={effect}:"
            f"duration={dur:.3f}:offset={offset:.3f}[{out_label}]"
        )
        current_label = out_label

    return ";\n".join(parts), "[v_out]"


def build_render_command(
    timeline_elements: list[dict],
    clip_file_map: dict[str, str],
    output_path: str,
    aspect_ratio: str = "16:9",
    quality: str = "final",
    caption_ass_path: str = None,
    encoder: str = None,
    crop_params: dict = None,
    fonts_dir: str = None,
) -> list[str]:
    """
    Build and return the complete FFmpeg argument list (not including 'ffmpeg' itself).

    Strategy:
    - Use concat filter to join clips sequentially
    - Apply aspect ratio crop/pad per clip if crop_params provided
    - Apply subtitle burn-in if caption_ass_path provided
    - Insert transitions (fade/cut/wipe) between clips using xfade filter
    - Title cards rendered as color video with drawtext

    For preview quality:
        -c:v libx264 -preset ultrafast -crf 28 -vf scale=1280:-2
        -c:a aac -b:a 128k

    For final quality (NVENC):
        -c:v h264_nvenc -preset p4 -cq 23
        -c:a aac -b:a 192k
        (fallback to libx264 -preset slow -crf 20 if no NVENC)

    Output resolution:
        16:9 → 1920x1080 (final) or 1280x720 (preview)
        9:16 → 1080x1920 (final) or 720x1280 (preview)
        1:1  → 1080x1080 (final) or 720x720  (preview)

    Returns: list of strings suitable for subprocess.run(["ffmpeg"] + args)
    """
    from kairos.config import VIDEO_ENCODER

    if encoder is None:
        encoder = VIDEO_ENCODER if quality == "final" else "libx264"

    W, H = _get_resolution(aspect_ratio, quality)

    # ── Separate elements by type ──────────────────────────────────────────────
    clip_elements = [e for e in timeline_elements if e.get("element_type") == "clip"]
    transition_elements = [e for e in timeline_elements if e.get("element_type") == "transition"]
    title_card_elements = [e for e in timeline_elements if e.get("element_type") == "title_card"]

    if not clip_elements and not title_card_elements:
        raise ValueError("Timeline has no clip or title_card elements — cannot render")

    # ── Build ordered segments (clips + title cards merged by position) ────────
    all_segments = sorted(
        clip_elements + title_card_elements,
        key=lambda e: e.get("position", 0),
    )

    # ── Validate clip file map ─────────────────────────────────────────────────
    missing = []
    for el in clip_elements:
        cid = el.get("clip_id")
        if cid and cid not in clip_file_map:
            missing.append(cid)
    if missing:
        logger.warning("build_render_command: %d clip(s) missing from clip_file_map: %s",
                       len(missing), missing[:5])

    # ── Build input list and filter_complex ───────────────────────────────────
    args: list[str] = ["-y"]   # overwrite output

    inputs: list[str] = []     # will become -i args
    filter_parts: list[str] = []
    concat_inputs: list[str] = []  # [label] pairs for concat
    audio_concat_inputs: list[str] = []
    input_idx = 0
    has_audio = False

    for seg_pos, seg in enumerate(all_segments):
        el_type = seg.get("element_type")
        params = _parse_params(seg)

        if el_type == "clip":
            cid = seg.get("clip_id", "")
            file_path = clip_file_map.get(cid)
            if not file_path:
                logger.warning("build_render_command: clip_id %s not in clip_file_map, skipping", cid)
                continue

            inputs.extend(["-i", file_path])

            # Crop filter for this clip if provided
            vf_parts: list[str] = []
            if crop_params and cid in crop_params:
                cp = crop_params[cid]
                vf_parts.append(
                    f"crop={cp['w']}:{cp['h']}:{cp['x']}:{cp['y']}"
                )
            vf_parts.append(f"scale={W}:{H}:force_original_aspect_ratio=decrease")
            vf_parts.append(f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
            vf_parts.append("setsar=1")

            vf_str = ",".join(vf_parts)
            filter_parts.append(f"[{input_idx}:v]{vf_str}[vclip{seg_pos}]")
            filter_parts.append(f"[{input_idx}:a]aresample=44100[aclip{seg_pos}]")
            concat_inputs.append(f"[vclip{seg_pos}]")
            audio_concat_inputs.append(f"[aclip{seg_pos}]")
            has_audio = True
            input_idx += 1

        elif el_type == "title_card":
            duration_sec = _ms_to_sec(seg.get("duration_ms", 3000))
            bg_color = params.get("color", "black")
            text = params.get("text", "").replace("'", "\\'").replace(":", "\\:")
            font_size = params.get("font_size", 48)
            font_color = params.get("font_color", "white")
            drawtext = (
                f"drawtext=text='{text}':fontsize={font_size}:fontcolor={font_color}:"
                f"x=(w-text_w)/2:y=(h-text_h)/2"
            )
            filter_parts.append(
                f"color=c={bg_color}:s={W}x{H}:d={duration_sec:.3f}[tc_raw{seg_pos}];"
                f"[tc_raw{seg_pos}]{drawtext}[vtc{seg_pos}]"
            )
            # Title cards: silence audio
            filter_parts.append(
                f"aevalsrc=0:d={duration_sec:.3f}:s=44100:c=stereo[atc{seg_pos}]"
            )
            concat_inputs.append(f"[vtc{seg_pos}]")
            audio_concat_inputs.append(f"[atc{seg_pos}]")

    if not concat_inputs:
        raise ValueError("No renderable segments found (all clips missing from clip_file_map)")

    n_segs = len(concat_inputs)

    # ── Decide on transitions ─────────────────────────────────────────────────
    # Build position→transition map
    trans_map: dict[int, dict] = {}
    for t_el in transition_elements:
        pos = t_el.get("position", 0)
        trans_map[pos] = _parse_params(t_el)

    # Check if any non-cut transitions exist between consecutive segments
    has_xfade = any(
        trans_map.get(i, {}).get("type", "cut") not in ("cut", "")
        for i in range(n_segs - 1)
    )

    if n_segs == 1:
        # Only one segment
        filter_parts.append(f"{concat_inputs[0]}null[v_concat]")
        if audio_concat_inputs:
            filter_parts.append(f"{audio_concat_inputs[0]}anull[a_concat]")
    elif not has_xfade:
        # Simple concat
        v_in = "".join(concat_inputs)
        a_in = "".join(audio_concat_inputs)
        filter_parts.append(
            f"{v_in}concat=n={n_segs}:v=1:a=0[v_concat]"
        )
        if audio_concat_inputs:
            filter_parts.append(
                f"{a_in}concat=n={n_segs}:v=0:a=1[a_concat]"
            )
    else:
        # xfade between pairs
        current_v = concat_inputs[0].strip("[]")
        current_a = audio_concat_inputs[0].strip("[]") if audio_concat_inputs else None

        for i in range(1, n_segs):
            t_info = trans_map.get(i - 1, {})
            t_type = t_info.get("type", "cut")
            dur = _ms_to_sec(int(t_info.get("duration_ms", 500)))

            # Estimate offset: sum of clip durations up to segment i-1 minus transition
            # Using element start_ms for precision
            seg_obj = all_segments[i - 1]
            seg_dur_ms = seg_obj.get("duration_ms", 3000)
            # offset = cumulative video length up to this xfade point
            # simplified: use start_ms of the segment being faded out
            offset = _ms_to_sec(seg_obj.get("start_ms", 0) + seg_dur_ms) - dur
            if offset < 0:
                offset = 0.0

            next_v = concat_inputs[i].strip("[]")
            out_v = f"xfv{i}" if i < n_segs - 1 else "v_concat"

            if t_type == "fade":
                effect = "fade"
            elif t_type in ("wipe", "wipe_left"):
                effect = "wipeleft"
            elif t_type == "wipe_right":
                effect = "wiperight"
            else:
                effect = "fade"

            filter_parts.append(
                f"[{current_v}][{next_v}]xfade=transition={effect}:"
                f"duration={dur:.3f}:offset={offset:.3f}[{out_v}]"
            )
            current_v = out_v

            if current_a and audio_concat_inputs:
                next_a = audio_concat_inputs[i].strip("[]")
                out_a = f"xfa{i}" if i < n_segs - 1 else "a_concat"
                filter_parts.append(
                    f"[{current_a}][{next_a}]acrossfade=d={dur:.3f}[{out_a}]"
                )
                current_a = out_a

    # ── Caption burn-in ───────────────────────────────────────────────────────
    final_v_label = "v_concat"
    if caption_ass_path:
        # Escape path for FFmpeg filter
        safe_ass = caption_ass_path.replace("\\", "/").replace("'", "\\'").replace(":", "\\:")
        # Pass fontsdir so FFmpeg resolves bundled fonts by name in the ASS file
        if fonts_dir:
            safe_fontsdir = str(fonts_dir).replace("\\", "/").replace("'", "\\'").replace(":", "\\:")
            subtitle_filter = f"subtitles='{safe_ass}':fontsdir='{safe_fontsdir}'"
        else:
            subtitle_filter = f"subtitles='{safe_ass}'"
        filter_parts.append(f"[v_concat]{subtitle_filter}[v_out]")
        final_v_label = "v_out"
    else:
        filter_parts.append(f"[v_concat]null[v_out]")
        final_v_label = "v_out"

    # ── Assemble full args ────────────────────────────────────────────────────
    # Inputs first
    for inp in inputs:
        args.append(inp)

    # filter_complex
    filter_complex = ";\n".join(filter_parts)
    args.extend(["-filter_complex", filter_complex])

    # Map output streams
    args.extend(["-map", f"[{final_v_label}]"])
    if has_audio and audio_concat_inputs:
        args.extend(["-map", "[a_concat]"])
    elif has_audio:
        # fallback audio from first input
        args.extend(["-map", "0:a?"])

    # ── Encoder settings ──────────────────────────────────────────────────────
    if quality == "preview":
        args.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
        ])
        if has_audio and audio_concat_inputs:
            args.extend(["-c:a", "aac", "-b:a", "128k"])
    else:
        # final quality
        if encoder == "h264_nvenc":
            args.extend([
                "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-cq", "23",
            ])
        else:
            args.extend([
                "-c:v", "libx264",
                "-preset", "slow",
                "-crf", "20",
            ])
        if has_audio and audio_concat_inputs:
            args.extend(["-c:a", "aac", "-b:a", "192k"])

    # Web streaming optimization
    args.extend(["-movflags", "+faststart"])

    # Output
    args.append(output_path)

    logger.debug("build_render_command: %d inputs, %d filter parts", len(inputs) // 2, len(filter_parts))
    return args
