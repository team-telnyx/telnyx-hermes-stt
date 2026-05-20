"""Runtime tests for _transcribe_telnyx.

Mocks the ``openai`` package so no network or API key is needed.
Validates the full transcription flow, error cases, and return shape.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_module(monkeypatch, api_key: str = "test-key"):
    """Load telnyx_stt_provider with a fresh import, setting env vars."""
    monkeypatch.setenv("TELNYX_API_KEY", api_key) if api_key else \
        monkeypatch.delenv("TELNYX_API_KEY", raising=False)

    sys.path.insert(0, str(ROOT))
    try:
        import importlib
        import telnyx_stt_provider as mod
        importlib.reload(mod)
        return mod
    finally:
        sys.path.pop(0)


def _stub_openai_client(monkeypatch, transcript_text: str = "Hello world"):
    """Return a fake OpenAI client whose transcriptions.create returns *transcript_text*."""
    fake_transcription = MagicMock()
    fake_transcription.text = transcript_text

    fake_client = MagicMock()
    fake_client.audio.transcriptions.create.return_value = fake_transcription
    fake_client.close = MagicMock()

    FakeOpenAI = MagicMock(return_value=fake_client)

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = FakeOpenAI
    fake_openai.APIError = Exception
    fake_openai.APIConnectionError = Exception
    fake_openai.APITimeoutError = Exception

    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    return fake_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_transcribe_telnyx_success(tmp_path, monkeypatch):
    """Happy path: returns success dict with transcript."""
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"FAKEAUDIO")

    _stub_openai_client(monkeypatch, transcript_text="Hello world")
    mod = _load_module(monkeypatch)

    result = mod._transcribe_telnyx(str(audio), "openai/whisper-large-v3-turbo")

    assert result["success"] is True
    assert result["transcript"] == "Hello world"
    assert result["provider"] == "telnyx"
    assert "error" not in result


def test_transcribe_telnyx_passes_correct_model(tmp_path, monkeypatch):
    """The model name should be forwarded to the OpenAI client."""
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"FAKEAUDIO")

    fake_client = _stub_openai_client(monkeypatch)
    mod = _load_module(monkeypatch)

    mod._transcribe_telnyx(str(audio), "openai/whisper-large-v3-turbo")

    call_kwargs = fake_client.audio.transcriptions.create.call_args
    assert call_kwargs.kwargs.get("model") == "openai/whisper-large-v3-turbo"


def test_transcribe_telnyx_passes_language_hint(tmp_path, monkeypatch):
    """TELNYX_STT_LANGUAGE should be forwarded to the OpenAI-compatible request."""
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"FAKEAUDIO")

    monkeypatch.setenv("TELNYX_STT_LANGUAGE", "es")
    fake_client = _stub_openai_client(monkeypatch)
    mod = _load_module(monkeypatch)

    mod._transcribe_telnyx(str(audio), "openai/whisper-large-v3-turbo")

    call_kwargs = fake_client.audio.transcriptions.create.call_args
    assert call_kwargs.kwargs.get("language") == "es"


def test_transcribe_telnyx_uses_telnyx_base_url(tmp_path, monkeypatch):
    """OpenAI client must be initialised with the Telnyx base URL."""
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"FAKEAUDIO")

    fake_openai = types.ModuleType("openai")
    captured_base_url = []

    def FakeOpenAI(api_key, base_url, **kwargs):
        captured_base_url.append(base_url)
        client = MagicMock()
        client.audio.transcriptions.create.return_value = MagicMock(text="hi")
        client.close = MagicMock()
        return client

    fake_openai.OpenAI = FakeOpenAI
    fake_openai.APIError = Exception
    fake_openai.APIConnectionError = Exception
    fake_openai.APITimeoutError = Exception
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    mod = _load_module(monkeypatch)
    mod._transcribe_telnyx(str(audio), "openai/whisper-large-v3-turbo")

    assert captured_base_url, "OpenAI was never instantiated"
    assert "telnyx.com" in captured_base_url[0], (
        f"Expected Telnyx base URL, got: {captured_base_url[0]}"
    )


def test_transcribe_telnyx_custom_base_url(tmp_path, monkeypatch):
    """TELNYX_STT_BASE_URL env var should override the default base URL."""
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"FAKEAUDIO")

    captured = []

    fake_openai = types.ModuleType("openai")

    def FakeOpenAI(api_key, base_url, **kwargs):
        captured.append(base_url)
        c = MagicMock()
        c.audio.transcriptions.create.return_value = MagicMock(text="ok")
        c.close = MagicMock()
        return c

    fake_openai.OpenAI = FakeOpenAI
    fake_openai.APIError = Exception
    fake_openai.APIConnectionError = Exception
    fake_openai.APITimeoutError = Exception
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setenv("TELNYX_STT_BASE_URL", "https://staging.example.com/v2/ai")

    mod = _load_module(monkeypatch)
    mod._transcribe_telnyx(str(audio), "openai/whisper-large-v3-turbo")

    assert "staging.example.com" in captured[0]


def test_transcribe_telnyx_no_api_key(tmp_path, monkeypatch):
    """Missing TELNYX_API_KEY should return failure dict."""
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"FAKEAUDIO")

    _stub_openai_client(monkeypatch)
    mod = _load_module(monkeypatch, api_key="")

    result = mod._transcribe_telnyx(str(audio), "openai/whisper-large-v3-turbo")

    assert result["success"] is False
    assert "TELNYX_API_KEY" in result["error"]


def test_transcribe_telnyx_permission_error(tmp_path, monkeypatch):
    """PermissionError on file open should return a failure dict."""
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"FAKEAUDIO")

    fake_openai = types.ModuleType("openai")

    def FakeOpenAI(**kwargs):
        c = MagicMock()
        c.audio.transcriptions.create.side_effect = PermissionError("denied")
        c.close = MagicMock()
        return c

    fake_openai.OpenAI = FakeOpenAI
    fake_openai.APIError = Exception
    fake_openai.APIConnectionError = Exception
    fake_openai.APITimeoutError = Exception
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    mod = _load_module(monkeypatch)
    result = mod._transcribe_telnyx(str(audio), "openai/whisper-large-v3-turbo")

    assert result["success"] is False
    assert "Permission denied" in result["error"]
