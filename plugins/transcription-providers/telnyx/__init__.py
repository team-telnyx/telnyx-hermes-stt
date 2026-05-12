"""Telnyx STT transcription provider for Hermes Agent.

Registers ``telnyx-stt`` as a first-class transcription provider using the
Telnyx Speech-to-Text API.

REST endpoint:
  ``https://api.telnyx.com/v2/ai/audio/transcriptions``
  Override with the ``TELNYX_STT_BASE_URL`` env var.

Request contract:
  1. POST ``multipart/form-data`` with ``Authorization: Bearer <TELNYX_API_KEY>``
  2. Include an audio ``file`` part
  3. Include ``model`` (default: ``openai/whisper-large-v3-turbo``)
  4. Optionally include ``language`` (ISO-639-1 hint, default: ``en``)
  5. Response contains a ``text`` field with the transcript
"""

from __future__ import annotations

import os

try:
    from hermes_cli import __version__ as _HERMES_VERSION
except ModuleNotFoundError as _err:
    raise ModuleNotFoundError(
        "Hermes Agent is not installed. Install Hermes first, then copy "
        "this plugin into ~/.hermes/plugins/transcription-providers/telnyx/."
    ) from _err

from providers import register_transcription_provider
from providers.base import TranscriptionProviderProfile

# ── Constants ─────────────────────────────────────────────────────────

TELNYX_STT_DEFAULT_BASE_URL = "https://api.telnyx.com/v2/ai/audio/transcriptions"
TELNYX_STT_BASE_URL = os.environ.get("TELNYX_STT_BASE_URL", TELNYX_STT_DEFAULT_BASE_URL)
TELNYX_STT_DEFAULT_MODEL = "openai/whisper-large-v3-turbo"
TELNYX_STT_DEFAULT_LANGUAGE = os.environ.get("TELNYX_STT_LANGUAGE", "en")

# File formats accepted by the Telnyx STT endpoint. Hermes can use this as
# offline discovery / validation metadata before making the live request.
TELNYX_STT_SUPPORTED_FORMATS = (
    "audio/mpeg",  # .mp3
    "audio/wav",   # .wav
    "audio/ogg",   # .ogg
    "audio/mp4",   # .m4a
    "audio/webm",  # .webm
)

# Curated model list for local discovery. Telnyx may expose additional models
# over time; keep the default stable and documented.
TELNYX_STT_FALLBACK_MODELS = (
    "openai/whisper-large-v3-turbo",
)

# ── Provider profile ──────────────────────────────────────────────────

telnyx_stt = TranscriptionProviderProfile(
    name="telnyx-stt",
    aliases=("telnyx-transcription", "telnyx-speech-to-text"),
    display_name="Telnyx STT",
    description=(
        "Telnyx Speech-to-Text — multipart audio transcription powered by "
        "Telnyx-hosted Whisper-compatible models"
    ),
    signup_url="https://portal.telnyx.com/#/app/api-keys",
    env_vars=("TELNYX_API_KEY", "TELNYX_STT_BASE_URL", "TELNYX_STT_LANGUAGE"),
    base_url=TELNYX_STT_BASE_URL,
    auth_type="api_key",
    default_headers={"User-Agent": f"HermesAgent/{_HERMES_VERSION}"},
    default_model=TELNYX_STT_DEFAULT_MODEL,
    fallback_models=TELNYX_STT_FALLBACK_MODELS,
    default_language=TELNYX_STT_DEFAULT_LANGUAGE,
    supported_formats=TELNYX_STT_SUPPORTED_FORMATS,
    request_format="multipart/form-data",
    response_text_path="text",
    supports_streaming=False,
)

register_transcription_provider(telnyx_stt)
