"""Runtime smoke test for the Telnyx STT Hermes transcription-provider plugin.

Stubs the minimal Hermes modules the plugin imports, then loads the plugin
exactly as Hermes' plugin discovery would — verifying that the provider
registers correctly without requiring Hermes to be installed.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "transcription-providers" / "telnyx" / "__init__.py"


def test_plugin_import_registers_telnyx_stt_provider(monkeypatch):
    registered = []

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.__version__ = "0.0-test"

    providers = types.ModuleType("providers")

    def register_transcription_provider(profile):
        registered.append(profile)

    providers.register_transcription_provider = register_transcription_provider

    providers_base = types.ModuleType("providers.base")

    class TranscriptionProviderProfile:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)

    providers_base.TranscriptionProviderProfile = TranscriptionProviderProfile

    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "providers", providers)
    monkeypatch.setitem(sys.modules, "providers.base", providers_base)

    spec = importlib.util.spec_from_file_location("telnyx_stt_runtime_test", PLUGIN)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert len(registered) == 1
    profile = registered[0]

    assert profile.name == "telnyx-stt"
    assert profile.aliases == ("telnyx-transcription", "telnyx-speech-to-text")
    assert profile.base_url == "https://api.telnyx.com/v2/ai/audio/transcriptions"
    assert profile.auth_type == "api_key"
    assert profile.env_vars == (
        "TELNYX_API_KEY",
        "TELNYX_STT_BASE_URL",
        "TELNYX_STT_LANGUAGE",
    )
    assert profile.default_headers == {"User-Agent": "HermesAgent/0.0-test"}
    assert profile.default_model == "openai/whisper-large-v3-turbo"
    assert profile.default_language == "en"
    assert "audio/wav" in profile.supported_formats
    assert profile.request_format == "multipart/form-data"
    assert profile.response_text_path == "text"
    assert profile.supports_streaming is False
