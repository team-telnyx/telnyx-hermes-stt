---
name: telnyx-hermes-stt
description: Install and validate the Telnyx STT transcription provider for Hermes Agent.
metadata: {"clawdbot":{"emoji":"🎙️","requires":{"env":["TELNYX_API_KEY"]},"primaryEnv":"TELNYX_API_KEY"}}
---

# Telnyx Hermes STT Provider

Use this skill when installing or validating the Telnyx Speech-to-Text provider for Hermes.

## Provider identity

- Provider ID: `telnyx-stt`
- Aliases: `telnyx-transcription`, `telnyx-speech-to-text`
- Hermes plugin path: `~/.hermes/plugins/transcription-providers/telnyx/`
- Telnyx endpoint: `https://api.telnyx.com/v2/ai/audio/transcriptions`
- Default model: `openai/whisper-large-v3-turbo`

## Install

```bash
mkdir -p ~/.hermes/plugins/transcription-providers
cp -R plugins/transcription-providers/telnyx \
  ~/.hermes/plugins/transcription-providers/telnyx
```

## Configure

```bash
export TELNYX_API_KEY="KEY..."
```

Optional:

```bash
export TELNYX_STT_BASE_URL="https://api.telnyx.com/v2/ai/audio/transcriptions"
export TELNYX_STT_LANGUAGE="en"
```

## Validate

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip pytest
python -m pytest -q
```

Live validation is skipped unless `TELNYX_API_KEY` is set:

```bash
python -m pytest -q tests/test_telnyx_stt_live.py
```

## Notes

- The plugin is copy-installed, matching the Hermes TTS provider pattern.
- The endpoint override is implemented via `TELNYX_STT_BASE_URL` and covered by tests.
- Local tests use a Hermes stub if Hermes is not installed.
