"""Telnyx STT built-in provider for Hermes Agent.

This module is a **contribution to hermes-agent**, not a standalone plugin.
It contains the implementation that should be integrated into
``tools/transcription_tools.py`` in the `team-telnyx/hermes-agent
<https://github.com/team-telnyx/hermes-agent>`_ repository.

Integration steps
-----------------
See README.md for the full patch instructions.  In brief:

1. Add the constants below to the top of ``transcription_tools.py``.
2. Copy ``_transcribe_telnyx`` into ``transcription_tools.py`` near the other
   ``_transcribe_*`` functions.
3. Add the dispatch branch in ``transcribe_audio``:

   .. code-block:: python

       if provider == "telnyx":
           model_name = model or TELNYX_STT_DEFAULT_MODEL
           return _transcribe_telnyx(file_path, model_name)

4. No new package dependency is needed — the existing ``openai`` package
   (already in Hermes) is used with the Telnyx base URL.

Endpoint
--------
The Telnyx STT endpoint is OpenAI-compatible:

    POST https://api.telnyx.com/v2/ai/audio/transcriptions
    Authorization: Bearer <TELNYX_API_KEY>

The ``openai`` Python client is pointed at the Telnyx base URL, so the
integration is a near-copy of the existing ``_transcribe_openai`` function.

Environment variables
---------------------
``TELNYX_API_KEY``
    Required — Bearer token (create at https://portal.telnyx.com/#/app/api-keys).
``TELNYX_STT_BASE_URL``
    Optional — override the base URL (strip the ``/audio/transcriptions`` suffix).
``TELNYX_STT_LANGUAGE``
    Optional — ISO-639-1 language hint (default: ``en``).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ── Constants (add/merge these into tools/transcription_tools.py) ──────────

TELNYX_STT_DEFAULT_BASE_URL = "https://api.telnyx.com/v2/ai"
TELNYX_STT_DEFAULT_MODEL = "openai/whisper-large-v3-turbo"
TELNYX_STT_DEFAULT_LANGUAGE = os.environ.get("TELNYX_STT_LANGUAGE", "en")

# ── Env helper ────────────────────────────────────────────────────────────
# In transcription_tools.py this function already exists at module level.
# This copy is only used when running this file standalone / in tests.

def _get_env_value(name: str, default: Optional[str] = None) -> Optional[str]:
    """Read env values; defers to hermes_cli.config when available."""
    try:
        from hermes_cli.config import get_env_value as _gev
    except ImportError:
        return os.getenv(name, default)
    val = _gev(name)
    return default if val is None else val


# ── OpenAI availability flag ───────────────────────────────────────────────
# In transcription_tools.py the equivalent is _HAS_OPENAI (computed at module
# import time). Here we check at call time so tests can monkeypatch sys.modules.

def _openai_available() -> bool:
    """Return True if the openai package is importable."""
    try:
        import openai  # noqa: F401
        return True
    except ImportError:
        return False


# ── Provider implementation ────────────────────────────────────────────────

def _transcribe_telnyx(file_path: str, model_name: str) -> Dict[str, Any]:
    """Transcribe audio using the Telnyx STT API (OpenAI-compatible endpoint).

    Drop this function into ``tools/transcription_tools.py`` alongside the
    other ``_transcribe_*`` helpers, then add the dispatch branch described in
    the module docstring.

    Note: when integrated into ``transcription_tools.py``:
    - Replace ``_get_env_value`` with the existing ``get_env_value``.
    - Replace ``_HAS_OPENAI`` with the existing module-level ``_HAS_OPENAI``.
    - ``_extract_transcript_text`` already exists in that module — use it.

    Args:
        file_path:  Absolute path to the audio file to transcribe.
        model_name: Whisper-compatible model name (e.g. ``openai/whisper-large-v3-turbo``).

    Returns:
        dict with keys:
          - ``"success"`` (bool)
          - ``"transcript"`` (str) — empty on failure
          - ``"provider"`` (str) — ``"telnyx"`` on success
          - ``"error"`` (str, optional) — error message on failure
    """
    # In transcription_tools.py replace _get_env_value → get_env_value
    _env = _get_env_value
    api_key = (_env("TELNYX_API_KEY") or "").strip()
    if not api_key:
        return {
            "success": False,
            "transcript": "",
            "error": (
                "TELNYX_API_KEY is not set. "
                "Create an API key at https://portal.telnyx.com/#/app/api-keys"
            ),
        }

    base_url = str(
        _env("TELNYX_STT_BASE_URL") or TELNYX_STT_DEFAULT_BASE_URL
    ).strip().rstrip("/")
    language = str(
        _env("TELNYX_STT_LANGUAGE") or TELNYX_STT_DEFAULT_LANGUAGE or ""
    ).strip()

    # In transcription_tools.py replace _openai_available() with the module-level _HAS_OPENAI.
    if not _openai_available():
        return {
            "success": False,
            "transcript": "",
            "error": "openai package not installed. Run: pip install openai",
        }

    try:
        from openai import OpenAI, APIError, APIConnectionError, APITimeoutError

        client = OpenAI(api_key=api_key, base_url=base_url, timeout=30, max_retries=0)
        try:
            with open(file_path, "rb") as audio_file:
                transcription_kwargs = {
                    "model": model_name,
                    "file": audio_file,
                    "response_format": "json",
                }
                if language:
                    transcription_kwargs["language"] = language

                transcription = client.audio.transcriptions.create(**transcription_kwargs)

            # _extract_transcript_text exists in transcription_tools.py.
            # Here we inline the same logic for standalone use.
            if hasattr(transcription, "text"):
                transcript_text = str(transcription.text).strip()
            elif isinstance(transcription, dict):
                transcript_text = str(transcription.get("text", "")).strip()
            else:
                transcript_text = str(transcription).strip()

            logger.info(
                "Transcribed %s via Telnyx STT (%s, %d chars)",
                Path(file_path).name,
                model_name,
                len(transcript_text),
            )
            return {"success": True, "transcript": transcript_text, "provider": "telnyx"}

        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    except PermissionError:
        return {"success": False, "transcript": "", "error": f"Permission denied: {file_path}"}
    except APIConnectionError as exc:
        return {"success": False, "transcript": "", "error": f"Connection error: {exc}"}
    except APITimeoutError as exc:
        return {"success": False, "transcript": "", "error": f"Request timeout: {exc}"}
    except APIError as exc:
        return {"success": False, "transcript": "", "error": f"API error: {exc}"}
    except Exception as exc:
        logger.error("Telnyx STT transcription failed: %s", exc, exc_info=True)
        return {"success": False, "transcript": "", "error": f"Transcription failed: {exc}"}
