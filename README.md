# VoiceCrashLab

VoiceCrashLab generates adversarial Indic voice-agent test suites, sends the original audio files to a configurable HTTP audio endpoint, and evaluates each response as soon as it arrives.

## Workflow

1. **Connect Agent**: enter the endpoint URL, optional token, multipart audio field, response text field (or response-audio URL field), and timeout. The dashboard checks endpoint reachability. The first real audio request validates the endpoint's actual request/response contract.
2. **Agent Info**: provide the agent role, business context, supported tasks, caller language, scenarios per track, and the TTS voice used to create caller recordings.
3. **Generate Test Suite**: creates speech and reasoning scenarios, records their clean audio, generates six attacks for each speech recording, and builds a manifest. With five scenarios per track, the default manifest contains 5 speech clean + 5 reasoning clean + 30 attacked speech files = 40 audio tests.
4. **Test Your Agent**: sends each manifest audio file to the configured endpoint. Each response is saved immediately and evaluated before the next test begins. A failure for one test does not erase results already collected.
5. **Evaluation Summary**: review expected behaviour, caller input, agent response, evaluation checks, and an LLM-generated suggested fix for failed cases.

## Setup (Windows PowerShell)

```powershell
cd path\to\VoiceCrashLab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Add `GROQ_API_KEY` to `.env`. Set `GROQ_SCENARIO_MODEL` and `GROQ_JUDGE_MODEL` to models available to your account.

The attack generator prefers real background samples in `data/background_noise/` (`traffic.wav`, `fan.wav`, `crowd.wav`). If absent, it creates clearly labelled synthetic ambience proxies so the suite can still be generated locally.

Run the dashboard:

```powershell
streamlit run dashboard\dashboard_app.py
```

## Endpoint contract

The target endpoint receives an HTTP `POST` with multipart form data. The uploaded file field is configurable. The endpoint may return raw audio bytes, JSON with a text response (configure `response_text_field`, including dotted paths such as `data.answer`), or JSON with a response-audio URL (configure `response_audio_url_field`). Authentication header and scheme are configurable too.

Connection checking verifies reachability; it cannot prove the API accepts the exact audio schema until a test audio is sent. That first real request is handled and recorded as a per-test result.

## Tests

```powershell
pytest -q
```

On Windows, install FFmpeg and ensure `ffmpeg.exe` is on `PATH`; pydub uses it to read/export MP3 files. VoiceCrashLab creates synthetic traffic/fan/crowd proxies if `data/background_noise/` does not contain real WAV samples. These proxies are reproducible test noise, not recordings of real environments.
