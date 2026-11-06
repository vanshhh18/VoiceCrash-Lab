# VoiceCrashLab

**A crash-test lab for Indic voice agents.** It generates hard Hinglish calls for a voice agent, adds realistic noise, sends the audio to the agent as a black box, and scores what comes back, so you can see where the agent breaks and whether the likely cause is *hearing* or *reasoning*.

Built for the [Gnani AI Great Indian AI Internship Challenge](https://www.gnani.ai/internship) using Gnani's **Timbre** and **Prisma**.

> 🎥 **Demo video:** `https://lnkd.in/p/gRUvHzpG` &nbsp;|&nbsp; 🔗 **LinkedIn post:** `https://lnkd.in/p/gRUvHzpG`

---

## Why this exists

Voice agents are usually tested on clean audio. Real callers are on busy roads, bad phone lines and crowded rooms, and they mix Hindi and English mid-sentence. A wrong digit in a phone number or a missed correction ("cancel nahi, date change karni hai") can mean a failed refund or a wrong account update. VoiceCrashLab makes those failures repeatable and measurable.

## How it works

```
Agent details (frontend form)
        |
        v
LLM       -> writes scenarios for that agent (speech track + reasoning track)
        |
        v
Timbre    -> speaks each scenario as caller audio
        |
        v
Audio attacks (speech track only) -> noise / phone line / dropouts / muffled
        |
        v
Target agent (black box)  <- audio in, text answer out
        |
        v
Prisma    -> reference transcript of the attacked audio (and of the agent's reply, if it answers in audio)
        |
        v
Judge     -> per-check verdict + failure category
        |
        v
Scorecard -> clean vs attacked, by attack type
```

### Gnani models used

| Model | Role in this project |
|---|---|
| **Groq LLM(GPT model)** | Generates adversarial scenarios|
| **Timbre** | Turns scenario scripts into caller audio |
| **Prisma** | Transcribes attacked audio (reference transcript) and agent audio replies |

### Sample agent (the thing being tested)

A small FastAPI voice agent: **Whisper** (speech-to-text), **Groq LLM**, **edge-tts** (speech output). The lab does not look inside it. Any agent that follows the contract below can be tested.

## Two test tracks

| Track | Scenarios | Audio | Purpose |
|---|---|---|---|
| **Speech** | 5 easy, clear requests with speech-sensitive details (numbers, times, names) | Clean **and** attacked | Does accuracy drop when the audio gets worse? |
| **Reasoning** | 5 hard requests (corrections, contradictions, ambiguity, capability limits) | Clean only | Does the agent reason correctly when hearing is not the problem? |

Reasoning scenarios are kept clean on purpose, so a failure points at reasoning and not at the audio.

## Audio attacks

Applied locally with fixed seeds and saved parameters, so results are reproducible.

| Attack | What it simulates |
|---|---|
| `traffic_noise` | Vehicles and horns |
| `fan_noise` | Steady background hum (easy baseline) |
| `crowd_noise` | Overlapping speech in the background (hardest noise) |
| `phone_line` | Narrow-band, low-sample-rate phone audio |
| `muffled_speech` | Distant speaker or covered mic |
| `audio_dropouts` | Dropped chunks, as on a bad network |

`TODO: add the SNR level(s) you used, e.g. 10 dB.`

## How a call is judged

The judge reads the scenario's expected behavior, the agent's reply, and the agent's declared capabilities, and returns five checks:

`goal_met` · `key_facts_correct` · `clarification_ok` · `no_hallucination` · `safety_ok`

A call passes only if all five are true. Failures get one category:

`INTENT_MISUNDERSTANDING`, `CONTEXT_FAILURE`, `MISSING_CLARIFICATION`, `OVER_CLARIFICATION`, `HALLUCINATION`, `SAFETY_FAILURE`, `IDENTITY_FAILURE`, `EMPATHY_FAILURE`, `UNKNOWN_FAILURE`

`TODO: update this list to match your final judge prompt (e.g. if you added TASK_NOT_COMPLETED).`

**Speech vs reasoning.** The lab compares the same scenario on clean and attacked audio, and checks the reference transcript against the original script (word error rate). If the agent passes clean and fails attacked, or the transcript is badly off, the failure is reported as a **likely perception issue**. It is *likely*, not confirmed, because a black-box agent's internal transcript is not visible.

## Quick start

```bash
git clone TODO_REPO_URL
cd TODO_REPO_NAME
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # then fill in your keys
```

`.env` (never commit this file):

```
GNANI_API_KEY=...        # TODO: use your actual variable names
GROQ_API_KEY=...
```

Start the sample agent:

```bash
uvicorn app.main:app --port 8000      # TODO: confirm module path
```

Run a crash test from the command line:

```bash
python run_crash_test.py \
  --role "Food Delivery Customer Support Agent" \
  --business "A food delivery platform handling customer orders and delivery issues" \
  --tasks "order tracking" "delivery rescheduling" "late delivery complaints" \
  --language Hinglish \
  --url "http://localhost:8000/voice"      # TODO: confirm endpoint
```

Or use the frontend: `TODO: command to start the frontend`, then open `TODO: URL`. A **Use demo agent** button runs the whole flow without any setup.

## Connect your own agent

`TODO: delete this section if the adapter is not finished.`

Your agent exposes one endpoint that accepts caller audio and returns a text answer or audio.

```
POST <your-url>
  audio: <wav file>        (multipart form field; name is configurable)

Response (either one):
  { "reply_text": "..." }
  { "reply_audio_b64": "..." }   # lab transcribes it with Prisma
```

You set the URL, optional auth, audio field name and response path in the form. Auth tokens stay on the server and are not saved. Requests to private or internal addresses are blocked.

## Results

`TODO: fill in from your final run. Use counts, not percentages, at this sample size.`

| Condition | Speech scenarios passed |
|---|---|
| Clean | `X / 5` |
| Traffic | `X / 5` |
| Crowd | `X / 5` |
| Fan | `X / 5` |
| Phone line | `X / 5` |
| Muffled | `X / 5` |
| Dropouts | `X / 5` |
| **Reasoning (clean)** | `X / 5` |

**Main finding:** `TODO: one honest sentence, e.g. what happened to numbers or digits under noise.`

**Judge check:** `TODO: "Judge agreed with my hand labels on X of 15 calls."`

Screenshots: `TODO: add scorecard and clean-vs-attacked screenshots to /docs and link them here.`

## Limitations

Please read these before drawing conclusions.

- **Synthetic speech and simulated noise.** Timbre audio with added noise is not the same as real callers. `TODO: if you tested real recordings, say so here.`
- **Small sample.** 10 scenarios, one run per condition unless stated. Results show examples, not statistics.
- **One sample agent tested.** Compatibility with other agents is designed (see the contract above) but not verified.
- **Single-message scenarios.** Each scenario is one caller turn, so multi-turn recovery is **not** measured.
- **Likely cause only.** Speech-vs-reasoning attribution is a signal, not proof.
- **LLM judge.** Validated on a small hand-labelled set (see Results). It can be wrong.
- **Sample agent has no backend.** `TODO: update if you added a mock backend or tools.`
- **Prisma's own errors** can appear in transcripts and in reply transcription. Results describe the whole pipeline, not Prisma alone.

## Responsible use

All data is synthetic. Do not use real phone numbers, Aadhaar, PAN, bank details or recorded customer calls. Do not point the lab at an agent connected to real customer data. Use a separate, limited test token for any agent you connect.

## Project structure

`TODO: verify against your repo.`

```
app/                 sample voice agent (FastAPI)
scenarios/           scenario generation, validation, storage
audio/               Timbre calls, audio attacks, Prisma transcription
evaluator/           benchmark runner, judge, scoring
data/benchmarks/     saved scenario suites
data/results/        saved run results
frontend/            scorecard and agent form
run_crash_test.py    command-line entry point
```

## Acknowledgements

Built with Gnani AI's Evon, Timbre and Prisma for the Great Indian AI Internship Challenge. Also uses `TODO: list main libraries, e.g. FastAPI, faster-whisper, edge-tts, Groq, jiwer, pydub`.

## Author

**Vansh Mittal** · [LinkedIn](https://linkedin.com/in/vanshmittal18) · [GitHub](https://github.com/vanshhh18)

## License

`TODO: choose a license, e.g. MIT, and add a LICENSE file.`
