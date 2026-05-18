# Telnyx STT — Hermes Agent Contribution

This repository contains the Telnyx Speech-to-Text provider implementation for
[Hermes Agent](https://github.com/NousResearch/hermes-agent).

It is **not** a standalone plugin. Hermes handles STT through built-in providers
dispatched in `tools/transcription_tools.py`. This repo contains the Telnyx
provider function and tests ready to be contributed upstream.

## What's inside

| File | Purpose |
|------|---------|
| `telnyx_stt_provider.py` | Drop-in implementation for `tools/transcription_tools.py` |
| `tests/test_telnyx_stt_static.py` | AST-based constant/signature checks (no credentials) |
| `tests/test_telnyx_stt_runtime.py` | Full transcription test with mocked openai client (no credentials) |
| `tests/test_telnyx_stt_live.py` | Live API test (requires `TELNYX_API_KEY`) |

## Integration into hermes-agent

### 1. Add the constants

Add to the constants section of `tools/transcription_tools.py`:

```python
TELNYX_STT_DEFAULT_BASE_URL = "https://api.telnyx.com/v2/ai"
TELNYX_STT_DEFAULT_MODEL    = "openai/whisper-large-v3-turbo"
TELNYX_STT_DEFAULT_LANGUAGE = os.environ.get("TELNYX_STT_LANGUAGE", "en")
```

### 2. Copy the provider function

Copy `_transcribe_telnyx` from `telnyx_stt_provider.py` into
`tools/transcription_tools.py` alongside the other `_transcribe_*` functions.

> **Note:** when integrating:
> - Replace `_get_env_value` with the existing module-level `get_env_value`.
> - Replace `_HAS_OPENAI` with the existing module-level `_HAS_OPENAI`.
> - Replace the inline transcript extraction with the existing `_extract_transcript_text` helper.

### 3. Add the dispatch branch

In `transcribe_audio`, add before the final `# No provider available` return:

```python
if provider == "telnyx":
    model_name = model or TELNYX_STT_DEFAULT_MODEL
    return _transcribe_telnyx(file_path, model_name)
```

### 4. No new dependencies

The existing `openai` package (already a Hermes dependency) is used with the
Telnyx base URL — no additional packages required.

## Provider details

| Field | Value |
|-------|-------|
| Provider ID | `telnyx` |
| Endpoint | `https://api.telnyx.com/v2/ai/audio/transcriptions` |
| Default model | `openai/whisper-large-v3-turbo` |
| Protocol | OpenAI-compatible (`multipart/form-data`) |
| Auth | `TELNYX_API_KEY` (Bearer) |
| Base URL override | `TELNYX_STT_BASE_URL` env var |
| Language override | `TELNYX_STT_LANGUAGE` env var (ISO-639-1, default `en`) |

## User configuration (`~/.hermes/config.yaml`)

```yaml
stt:
  provider: telnyx
  # Optional overrides:
  # telnyx:
  #   model: openai/whisper-large-v3-turbo
```

## Running tests

```bash
# No credentials needed
python -m pytest tests/test_telnyx_stt_static.py tests/test_telnyx_stt_runtime.py -q

# Live test (requires TELNYX_API_KEY)
export TELNYX_API_KEY=***
python -m pytest tests/test_telnyx_stt_live.py -q
```

## Linear

AIF-196

## References

- [Telnyx AI API docs](https://developers.telnyx.com/docs/ai)
- [Telnyx API keys](https://portal.telnyx.com/#/app/api-keys)
- [hermes-agent transcription_tools.py](https://github.com/NousResearch/hermes-agent/blob/main/tools/transcription_tools.py)
