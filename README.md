# Telnyx STT Provider for Hermes

Telnyx Speech-to-Text provider plugin for [Hermes Agent](https://github.com/team-telnyx/telapps-hermes) using the Telnyx AI transcription endpoint.

- Provider ID: `telnyx-stt`
- Aliases: `telnyx-transcription`, `telnyx-speech-to-text`
- Endpoint: `https://api.telnyx.com/v2/ai/audio/transcriptions`
- Default model: `openai/whisper-large-v3-turbo`
- Auth: `TELNYX_API_KEY`

## What this plugin does

This plugin registers a Hermes transcription-provider profile for Telnyx STT. It gives Hermes the endpoint, auth type, provider metadata, default model, supported audio formats, and response shape needed to send audio files to Telnyx for transcription.

The Telnyx API request is multipart form-data:

```text
POST /v2/ai/audio/transcriptions
Authorization: Bearer $TELNYX_API_KEY
Content-Type: multipart/form-data

file=<audio file>
model=openai/whisper-large-v3-turbo
language=en
```

The response includes a `text` field with the transcript.

## Installation

Install Hermes first, then copy this provider into Hermes' plugin directory:

```bash
mkdir -p ~/.hermes/plugins/transcription-providers
cp -R plugins/transcription-providers/telnyx \
  ~/.hermes/plugins/transcription-providers/telnyx
```

Expected files after install:

```text
~/.hermes/plugins/transcription-providers/telnyx/plugin.yaml
~/.hermes/plugins/transcription-providers/telnyx/__init__.py
```

## Configuration

Required:

```bash
export TELNYX_API_KEY="KEY..."
```

Optional:

```bash
# Override the default Telnyx transcription endpoint.
export TELNYX_STT_BASE_URL="https://api.telnyx.com/v2/ai/audio/transcriptions"

# ISO-639-1 language hint sent by Hermes when supported by its STT runtime.
export TELNYX_STT_LANGUAGE="en"
```

## Verify locally

Run the plugin tests:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip pytest
python -m pytest -q
```

Local tests do **not** require `TELNYX_API_KEY`. Live tests are skipped unless credentials are present.

## Verify in Hermes

After installing the plugin into `~/.hermes/plugins/transcription-providers/telnyx`, use the Hermes provider discovery command for your Hermes version. Expected result: provider `telnyx-stt` appears with aliases `telnyx-transcription` and `telnyx-speech-to-text`.

If Hermes is not installed locally, the runtime tests in this repo stub the minimal Hermes provider interface and verify that the plugin registers the expected profile.

## Live Telnyx verification

Set `TELNYX_API_KEY` and run:

```bash
python -m pytest -q tests/test_telnyx_stt_live.py
```

The live test posts a tiny generated WAV tone file to:

```text
https://api.telnyx.com/v2/ai/audio/transcriptions
```

It verifies that Telnyx returns a JSON response with a `text` field. The generated audio is a short tone, so the transcript may be empty; the contract validation is response-shape focused.

## Supported audio formats

- MP3: `audio/mpeg`
- WAV: `audio/wav`
- OGG: `audio/ogg`
- M4A: `audio/mp4`
- WebM: `audio/webm`

## Development notes

- The implementation intentionally mirrors the Hermes TTS provider pattern.
- `TELNYX_STT_BASE_URL` is read directly by plugin code, so endpoint overrides are test-covered.
- `plugin.yaml` name/provider ID and Python profile name all use `telnyx-stt` to avoid manifest/provider mismatch.
- `pyproject.toml` exists for metadata and test tooling; Hermes installation is copy-based.
