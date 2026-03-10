"""
Caption style presets and ASS header generation.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Built-in platform presets
PLATFORM_PRESETS: dict[str, dict] = {
    "tiktok": {
        "font_name": "Impact",
        "font_size": 72,
        "font_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 3,
        "shadow": 0,
        "position": "bottom",
        "animation_type": "word_highlight",
    },
    "youtube": {
        "font_name": "Arial",
        "font_size": 48,
        "font_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "position": "bottom",
        "animation_type": "none",
    },
    "instagram": {
        "font_name": "Helvetica",
        "font_size": 56,
        "font_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "position": "center",
        "animation_type": "none",
    },
}


def get_default_style() -> dict:
    """Return the default caption style dict."""
    return {
        "font_name": "Arial",
        "font_size": 48,
        "font_color": "#FFFFFF",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow": 1,
        "position": "bottom",
        "animation_type": "none",
    }


def hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
    """
    Convert #RRGGBB to ASS &HAABBGGRR format.
    ASS channels are reversed from HTML: R and B are swapped.
    alpha: 0 = fully opaque, 255 = fully transparent.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        logger.warning("hex_to_ass_color: invalid hex color '%s', defaulting to white", hex_color)
        return "&H00FFFFFF"

    r = hex_color[0:2]
    g = hex_color[2:4]
    b = hex_color[4:6]
    aa = f"{alpha:02X}"
    return f"&H{aa}{b}{g}{r}"


def _position_to_alignment(position: str) -> int:
    """
    Convert position string to ASS alignment numpad value.
    bottom=2, top=8, center=5
    """
    mapping = {
        "bottom": 2,
        "top": 8,
        "center": 5,
        "bottom_left": 1,
        "bottom_right": 3,
        "top_left": 7,
        "top_right": 9,
    }
    return mapping.get(position, 2)


def build_ass_header(style: dict, resolution: tuple[int, int]) -> str:
    """Build the [Script Info] + [V4+ Styles] section of an ASS file."""
    W, H = resolution
    alignment = _position_to_alignment(style.get("position", "bottom"))
    font_name = style.get("font_name", "Arial")
    font_size = int(style.get("font_size", 48))
    primary_color = hex_to_ass_color(style.get("font_color", "#FFFFFF"))
    outline_color = hex_to_ass_color(style.get("outline_color", "#000000"))
    shadow_color = hex_to_ass_color("#000000", alpha=128)
    outline_width = int(style.get("outline_width", 2))
    shadow_val = int(style.get("shadow", 1))

    # Margins: bottom=10% of height, top=10%, left/right=5% of width
    margin_v = int(H * 0.07)
    margin_lr = int(W * 0.05)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H00FFFFFF,{outline_color},{shadow_color},0,0,0,0,100,100,0,0,1,{outline_width},{shadow_val},{alignment},{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header


def _ms_to_ass_time(ms: int) -> str:
    """Convert milliseconds to ASS timestamp format: H:MM:SS.cc"""
    total_sec = ms / 1000.0
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = int(total_sec % 60)
    cs = int(round((total_sec - int(total_sec)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass_events(captions: list[dict], style: dict) -> str:
    """
    Build the [Events] section of an ASS file from caption cues.
    For word_highlight animation: each word gets its own timed override tag.
    For static: one line per caption cue.
    """
    animation_type = style.get("animation_type", "none")
    lines: list[str] = []

    for cue in captions:
        start_ts = _ms_to_ass_time(cue["start_ms"])
        end_ts = _ms_to_ass_time(cue["end_ms"])
        text = cue.get("text", "").replace("\n", "\\N")

        if animation_type == "word_highlight":
            words = cue.get("words", [])
            if words:
                # Build karaoke-style word highlight using {\k} tags
                # {\k<centiseconds>} delays before showing next syllable
                # We use {\1c&H00FFFF&} (yellow) for active word, default for others
                highlight_color = "&H0000FFFF"  # yellow in ASS BGR
                parts: list[str] = []
                cue_start_ms = cue["start_ms"]
                prev_end_ms = cue_start_ms

                for w_idx, w in enumerate(words):
                    w_start = w.get("start_ms", cue_start_ms)
                    w_end = w.get("end_ms", cue["end_ms"])
                    word_text = w.get("word", "")
                    # Duration of this word in centiseconds
                    dur_cs = max(1, int((w_end - w_start) / 10))
                    # Pre-gap (silence before this word) in centiseconds
                    gap_cs = max(0, int((w_start - prev_end_ms) / 10))

                    if gap_cs > 0:
                        parts.append(f"{{\\k{gap_cs}}}")
                    parts.append(f"{{\\kf{dur_cs}}}{word_text} ")
                    prev_end_ms = w_end

                ass_text = "".join(parts).rstrip()
                lines.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{ass_text}")
            else:
                # Fallback: static display
                lines.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}")
        else:
            # Static caption
            lines.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}")

    return "\n".join(lines)


def write_ass_file(
    captions: list[dict],
    style: dict,
    output_path: str,
    resolution: tuple[int, int] = (1920, 1080),
) -> str:
    """Write complete .ass file. Returns output_path."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    header = build_ass_header(style, resolution)
    events = build_ass_events(captions, style)
    content = header + events + "\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("write_ass_file: wrote %d cues to %s", len(captions), output_path)
    return output_path
