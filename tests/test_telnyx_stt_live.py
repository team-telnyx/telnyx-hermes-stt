"""Live Telnyx STT validation (env-gated, skipped without TELNYX_API_KEY).

Validates that the real Telnyx transcription endpoint accepts a small
generated WAV file and returns a valid JSON response.
"""

from __future__ import annotations

import math
import os
import sys
import tempfile
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY", "")
SKIP_REASON = "TELNYX_API_KEY not set — skipping live STT tests"


def _tiny_wav(path: Path) -> None:
    """Write a 100 ms 16 kHz mono 440 Hz tone WAV to *path*."""
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        frames = bytearray()
        for i in range(1600):
            sample = int(8000 * math.sin(2 * math.pi * 440 * i / 16000))
            frames.extend(sample.to_bytes(2, "little", signed=True))
        wav.writeframes(bytes(frames))


@pytest.mark.skipif(not TELNYX_API_KEY, reason=SKIP_REASON)
def test_live_transcription_returns_text(tmp_path):
    """The Telnyx STT endpoint should return success=True with a text field."""
    audio = tmp_path / "test.wav"
    _tiny_wav(audio)

    sys.path.insert(0, str(ROOT))
    try:
        import importlib
        import telnyx_stt_provider as mod
        importlib.reload(mod)

        result = mod._transcribe_telnyx(
            str(audio),
            mod.TELNYX_STT_DEFAULT_MODEL,
        )
    finally:
        sys.path.pop(0)

    assert result["success"] is True, f"Expected success, got: {result}"
    assert isinstance(result["transcript"], str)
    assert result["provider"] == "telnyx"
