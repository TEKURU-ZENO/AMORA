"""Podcast Audio Generation & Voice Date Cues.

Provides:
1. Dual-speaker audio cues with timing, mood, and voice pitch shifts.
2. Server-side MP3 synthesis with gTTS caching and offline fallback.
3. Mid-date human coaching whisper injections.
"""
from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path
from typing import Any, Optional

from .. import store
from ..models import DateRecord, Person

logger = logging.getLogger(__name__)


def get_first_name(p: Optional[Person], fallback_id: str) -> str:
    if p and p.analysis and p.analysis.display_name:
        return p.analysis.display_name.split()[0]
    return fallback_id


def build_audio_cues(
    d: DateRecord,
    pa: Optional[Person],
    pb: Optional[Person],
    authorized: bool = False,
) -> list[dict[str, Any]]:
    """Build structured turn-by-turn speech cues for Web Speech / audio playback."""
    name_a = get_first_name(pa, d.a)
    name_b = get_first_name(pb, d.b)

    cues: list[dict[str, Any]] = []
    current_time_sec = 0.0

    # Intro cue
    intro_text = f"Welcome to the date replay between {name_a} and {name_b} at {d.venue}."
    intro_words = len(intro_text.split())
    intro_duration = max(2.5, intro_words * (60.0 / 145.0))
    cues.append({
        "turn_index": -1,
        "speaker_id": "narrator",
        "speaker_name": "Host",
        "side": "narrator",
        "text": intro_text,
        "thought": "",
        "mood": "spark",
        "start_time_sec": round(current_time_sec, 2),
        "duration_sec": round(intro_duration, 2),
        "voice_settings": {
            "pitch": 1.0,
            "rate": 1.05,
            "tld": "com",
            "lang": "en-US",
        },
    })
    current_time_sec += intro_duration + 0.5

    for idx, t in enumerate(d.turns):
        is_a = (t.speaker == d.a)
        spk_name = name_a if is_a else name_b
        side = "a" if is_a else "b"

        # Calculate estimated duration based on word count (~145 wpm)
        words = len(t.text.split())
        turn_dur = max(1.8, words * (60.0 / 140.0))

        # Different voice settings for speaker A vs speaker B
        voice_cfg = {
            "pitch": 1.08 if is_a else 0.92,
            "rate": 1.0 if is_a else 0.98,
            "tld": "com" if is_a else "co.uk",
            "lang": "en-US" if is_a else "en-GB",
        }

        cue = {
            "turn_index": idx,
            "speaker_id": t.speaker,
            "speaker_name": spk_name,
            "side": side,
            "text": t.text,
            "thought": t.thought if authorized else "",
            "observation": t.observation if authorized else "",
            "whisper": getattr(t, "whisper", None) or "",
            "mood": t.mood,
            "start_time_sec": round(current_time_sec, 2),
            "duration_sec": round(turn_dur, 2),
            "voice_settings": voice_cfg,
        }
        cues.append(cue)
        current_time_sec += turn_dur + 0.4  # 400ms conversational cadence pause

    return cues


def get_audio_cache_path(date_id: str) -> Path:
    """Path to the cached MP3 file for a date."""
    cache_dir = store.DATA_DIR / "audio_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{date_id}.mp3"


def synthesize_date_mp3(
    d: DateRecord,
    pa: Optional[Person],
    pb: Optional[Person],
) -> Optional[bytes]:
    """Synthesize dual-speaker MP3 using gTTS if available, caching result to disk."""
    cache_file = get_audio_cache_path(d.id)
    if cache_file.exists():
        try:
            return cache_file.read_bytes()
        except Exception:
            pass

    try:
        from gtts import gTTS
    except ImportError:
        logger.warning("gTTS not installed, cannot synthesize server-side MP3.")
        return None

    # Synthesize sequential MP3 byte stream
    combined_mp3 = io.BytesIO()
    try:
        for t in d.turns[:12]:  # limit to standard date length
            is_a = (t.speaker == d.a)
            tld = "com" if is_a else "co.uk"
            buf = io.BytesIO()
            tts = gTTS(text=t.text, lang="en", tld=tld, slow=False)
            tts.write_to_fp(buf)
            combined_mp3.write(buf.getvalue())

        audio_bytes = combined_mp3.getvalue()
        if audio_bytes:
            cache_file.write_bytes(audio_bytes)
            return audio_bytes
    except Exception as e:
        logger.info("Online MP3 synthesis skipped (offline / sandbox): %s", e)
        return None

    return None
