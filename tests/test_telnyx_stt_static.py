"""Static validation for the Telnyx STT hermes-agent contribution.

Reads ``telnyx_stt_provider.py`` via AST — no imports, no credentials,
no network.  Validates constants, function signature, and README integration
instructions.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "telnyx_stt_provider.py"
README = ROOT / "README.md"


def _module_ast() -> ast.Module:
    return ast.parse(PROVIDER.read_text(encoding="utf-8"))


def _assigned_constant(name: str):
    for node in _module_ast().body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        return ast.literal_eval(node.value)
            else:
                if isinstance(node.target, ast.Name) and node.target.id == name and node.value:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"missing assignment for {name!r} in {PROVIDER.name}")


def test_provider_module_exists():
    assert PROVIDER.exists(), "telnyx_stt_provider.py not found in repo root"


def test_default_base_url():
    assert _assigned_constant("TELNYX_STT_DEFAULT_BASE_URL") == \
        "https://api.telnyx.com/v2/ai/openai"


def test_default_model():
    assert _assigned_constant("TELNYX_STT_DEFAULT_MODEL") == "openai/whisper-large-v3-turbo"


def test_transcribe_function_exists():
    source = PROVIDER.read_text(encoding="utf-8")
    assert "def _transcribe_telnyx(" in source


def test_transcribe_function_signature():
    source = PROVIDER.read_text(encoding="utf-8")
    assert "_transcribe_telnyx(file_path: str, model_name: str)" in source


def test_transcribe_function_returns_dict_shape():
    """Function must return dicts with 'success' and 'transcript' keys."""
    source = PROVIDER.read_text(encoding="utf-8")
    assert '"success": True' in source
    assert '"success": False' in source
    assert '"transcript"' in source
    assert '"provider": "telnyx"' in source


def test_openai_compatible_endpoint_used():
    """Must use the OpenAI client — openai package, not raw HTTP."""
    source = PROVIDER.read_text(encoding="utf-8")
    assert "from openai import OpenAI" in source
    assert "audio.transcriptions.create" in source


def test_readme_integration_instructions():
    readme = README.read_text(encoding="utf-8")
    assert "_transcribe_telnyx" in readme
    assert "transcription_tools.py" in readme
    assert "TELNYX_API_KEY" in readme
    assert "TELNYX_STT_DEFAULT_MODEL" in readme or "openai/whisper-large-v3-turbo" in readme
