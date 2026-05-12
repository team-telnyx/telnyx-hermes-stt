"""Static validation for the standalone Telnyx STT Hermes transcription provider."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "transcription-providers" / "telnyx" / "__init__.py"
MANIFEST = ROOT / "plugins" / "transcription-providers" / "telnyx" / "plugin.yaml"
README = ROOT / "README.md"
SKILL = ROOT / "SKILL.md"


def _module_ast() -> ast.Module:
    return ast.parse(PLUGIN.read_text(encoding="utf-8"))


def _assigned_constant(name: str):
    for node in _module_ast().body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"missing assignment for {name}")


def test_manifest_declares_transcription_provider():
    text = MANIFEST.read_text(encoding="utf-8")
    assert "kind: transcription-provider" in text
    assert "name: telnyx-stt" in text
    assert "provider_id: telnyx-stt" in text


def test_provider_constants():
    assert (
        _assigned_constant("TELNYX_STT_DEFAULT_BASE_URL")
        == "https://api.telnyx.com/v2/ai/audio/transcriptions"
    )
    assert _assigned_constant("TELNYX_STT_DEFAULT_MODEL") == "openai/whisper-large-v3-turbo"


def test_supported_formats_declared():
    formats = _assigned_constant("TELNYX_STT_SUPPORTED_FORMATS")
    assert formats == (
        "audio/mpeg",
        "audio/wav",
        "audio/ogg",
        "audio/mp4",
        "audio/webm",
    )


def test_provider_profile_shape_is_declared():
    source = PLUGIN.read_text(encoding="utf-8")
    assert 'name="telnyx-stt"' in source
    assert 'aliases=("telnyx-transcription", "telnyx-speech-to-text")' in source
    assert 'auth_type="api_key"' in source
    assert 'request_format="multipart/form-data"' in source
    assert 'response_text_path="text"' in source
    assert "supports_streaming=False" in source


def test_docs_are_consistent_with_source():
    endpoint = _assigned_constant("TELNYX_STT_DEFAULT_BASE_URL")
    model = _assigned_constant("TELNYX_STT_DEFAULT_MODEL")
    for path in (README, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "telnyx-stt" in text
        assert endpoint in text
        assert model in text
        assert "TELNYX_STT_BASE_URL" in text
        assert "~/.hermes/plugins/transcription-providers/telnyx" in text


def test_base_url_and_language_overrides_from_env(monkeypatch):
    import importlib.util
    import sys
    import types

    custom_url = "https://custom.example.com/v2/ai/audio/transcriptions"
    custom_language = "es"
    monkeypatch.setenv("TELNYX_STT_BASE_URL", custom_url)
    monkeypatch.setenv("TELNYX_STT_LANGUAGE", custom_language)

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.__version__ = "0.0-test"
    providers = types.ModuleType("providers")
    providers.register_transcription_provider = lambda p: None
    providers_base = types.ModuleType("providers.base")

    class FakeTPP:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    providers_base.TranscriptionProviderProfile = FakeTPP
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "providers", providers)
    monkeypatch.setitem(sys.modules, "providers.base", providers_base)

    spec = importlib.util.spec_from_file_location("telnyx_stt_env_test", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.TELNYX_STT_BASE_URL == custom_url
    assert mod.TELNYX_STT_DEFAULT_LANGUAGE == custom_language
    assert mod.telnyx_stt.base_url == custom_url
    assert mod.telnyx_stt.default_language == custom_language
