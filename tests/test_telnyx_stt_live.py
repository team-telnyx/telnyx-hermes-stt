"""Live Telnyx STT validation (env-gated, skipped by default).

Set TELNYX_API_KEY to run. Validates that the Telnyx transcription endpoint
accepts a small generated WAV file and returns the expected JSON shape.
"""

from __future__ import annotations

import ast
import json
import math
import os
import re
import tempfile
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "transcription-providers" / "telnyx" / "__init__.py"

TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY", "")
SKIP_REASON = "TELNYX_API_KEY not set — skipping live STT tests"


def _assigned_constant(name: str):
    tree = ast.parse(PLUGIN.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"missing assignment for {name}")


def _tiny_wav_bytes() -> bytes:
    """Generate a tiny 16 kHz mono WAV tone; no fixture files needed."""
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            frames = bytearray()
            for i in range(1600):  # 100 ms
                sample = int(8000 * math.sin(2 * math.pi * 440 * i / 16000))
                frames.extend(sample.to_bytes(2, "little", signed=True))
            wav.writeframes(bytes(frames))
        return Path(tmp.name).read_bytes()


def _redact_secret_ids(text: str) -> str:
    """Avoid leaking Telnyx key IDs or secrets in pytest failure output."""
    return re.sub(r"KEY[A-Z0-9_]+", "KEY…REDACTED", text)


def _multipart_body(audio: bytes, model: str, language: str | None = None) -> tuple[bytes, str]:
    if language is None:
        language = os.environ.get("TELNYX_STT_LANGUAGE", "en")
    boundary = f"----TelnyxHermesBoundary{uuid.uuid4().hex}"
    body: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        body.extend([
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"",
            value.encode(),
        ])

    body.extend([
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="telnyx-hermes-stt.wav"',
        b"Content-Type: audio/wav",
        b"",
        audio,
    ])
    add_field("model", model)
    add_field("language", language)
    body.extend([f"--{boundary}--".encode(), b""])
    return b"\r\n".join(body), boundary


@pytest.mark.skipif(not TELNYX_API_KEY, reason=SKIP_REASON)
def test_transcription_endpoint_returns_text_field():
    endpoint = os.environ.get("TELNYX_STT_BASE_URL", _assigned_constant("TELNYX_STT_DEFAULT_BASE_URL"))
    model = _assigned_constant("TELNYX_STT_DEFAULT_MODEL")
    language = os.environ.get("TELNYX_STT_LANGUAGE", "en")
    body, boundary = _multipart_body(_tiny_wav_bytes(), model, language)

    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {TELNYX_API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = _redact_secret_ids(exc.read().decode("utf-8", errors="replace"))
        pytest.fail(f"Telnyx STT endpoint returned HTTP {exc.code}: {error_body}")

    assert isinstance(payload, dict)
    assert "text" in payload
    assert isinstance(payload["text"], str)
