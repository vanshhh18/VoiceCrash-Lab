# VoiceCrashLab

**A crash-test lab for Indic voice agents.** It generates hard Hinglish calls for a voice agent, adds realistic noise, sends the audio to the agent as a black box, and scores what comes back, so you can see where the agent breaks and whether the likely cause is *hearing* or *reasoning*.

Built for the [Gnani AI Great Indian AI Internship Challenge](https://www.gnani.ai/internship) using Gnani's **Timbre** and **Prisma**, with a Groq-hosted LLM for scenario generation and judging.

🎥 **[Watch the demo video](https://lnkd.in/p/gRUvHzpG)**

---

## Why this exists

Voice agents are usually tested on clean audio. Real callers are on busy roads, bad phone lines and crowded rooms, and they mix Hindi and English mid-sentence. A wrong digit in a phone number or a missed correction ("cancel nahi, date change karni hai") can mean a failed refund or a wrong account update. VoiceCrashLab makes those failures repeatable and measurable.

## How it works

```
Agent details (role, business, tasks, language)
        |
        v
Groq LLM (GPT model)  -> writes scenarios for that agent
                         (speech track + reasoning track)
        |
        v
Timbre                -> speaks each scenario as caller audio
        |
        v
Audio attacks         -> noise / phone line / dropouts / muffled
(speech track only)
        |
        v
Target agent          -> black box: audio in, text answer out
        |
        v
Prisma                -> transcribes the attacked audio
        |
        v
Judge (Groq LLM)      -> per-check verdict + failure category
        |
        v
Scorecard             -> clean vs attacked, by attack type
```

### Models and tools

| Component | Role in this project |
|---|---|
| **Timbre** (Gnani) | Turns scenario scripts into caller audio |
| **Prisma** (Gnani) | Speech-to-text for the attacked caller audio |
| **Groq LLM (GPT model)** | Generates adversarial scenarios and judges the agent's replies |

### Sample agent (the thing being tested)

A small FastAPI voice agent built with **Whisper** (speech-to-text), a **Groq LLM (GPT model)** for reasoning, and **edge-tts** for speech output. The lab does not look inside it: it only sends audio and reads the answer, so any agent that accepts audio and returns an answer can be tested the same way.

## Two test tracks

| Track | Scenarios | Audio | Purpose |
|---|---|---|---|
| **Speech** | 5 easy, clear requests with speech-sensitive details (numbers, times, names) | Clean **and** attacked | Does accuracy drop when the audio gets worse? |
| **Reasoning** | 5 hard requests (corrections, contradictions, ambiguity, capability limits) | Clean only | Does the agent reason correctly when hearing is not the problem? |

Reasoning scenarios are kept clean on purpose, so a failure points at reasoning and not at the audio.

## Audio attacks

Applied locally, so they cost no API credits.

| Attack | What it simulates |
|---|---|
| `traffic_noise` | Vehicles and horns |
| `fan_noise` | Steady background hum |
| `crowd_noise` | Overlapping speech in the background |
| `phone_line` | Narrow-band, low-quality phone audio |
| `muffled_speech` | Distant speaker or covered mic |
| `audio_dropouts` | Dropped chunks, as on a bad network |

## How a call is judged

The judge reads the scenario's expected behavior, the agent's reply, and the agent's declared role and supported tasks, then returns five checks:

`goal_met` · `key_facts_correct` · `clarification_ok` · `no_hallucination` · `safety_ok`

A call passes only if all five are true. Failures get one category, such as `INTENT_MISUNDERSTANDING`, `CONTEXT_FAILURE`, `MISSING_CLARIFICATION`, `OVER_CLARIFICATION`, `HALLUCINATION` or `SAFETY_FAILURE`.

**Speech vs reasoning.** The lab compares the same scenario on clean and attacked audio. If the agent passes clean and fails attacked, the failure is reported as a **likely perception issue**. It is *likely*, not confirmed, because a black-box agent's internal transcript is not visible.

## Quick start

1. Clone the repository and create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Create a `.env` file with your Gnani (Timbre, Prisma) and Groq API keys. Never commit this file.

3. Start the sample agent:

```bash
uvicorn app.main:app --port 8000
```

4. Run a crash test from the command line:

```bash
python run_crash_test.py \
  --role "Food Delivery Customer Support Agent" \
  --business "A food delivery platform handling customer orders and delivery issues" \
  --tasks "order tracking" "delivery rescheduling" "late delivery complaints" \
  --language Hinglish \
  --url "http://localhost:8000/chat"
```

(In PowerShell, replace the trailing `\` with a backtick `` ` ``.)

The lab picks a matching saved test suite for the agent's role, business and language, or generates and saves a new one. Results are written to `data/results/`.

## Connect your own agent

You can test your own agent instead of the sample one. In the frontend, enter the agent's details (role, business context, supported tasks, language) and the agent's API endpoint, then start a run. The lab sends the generated caller audio to that endpoint and evaluates the answer that comes back, without needing access to the agent's internals.

Only connect agents that run on test or synthetic data, never one that is connected to real customer data.

## Results

Counts, not percentages, because each condition has only 5 scenarios.
Counted on dummy customer support food delivery agent.

| Condition | Scenarios passed |
|---|---|
| Speech, clean | 4 / 5 |
| Speech, traffic noise | 2 / 5 |
| Speech, crowd noise | 2 / 5 |
| Speech, fan noise | 1 / 5 |
| Speech, phone line | 3 / 5 |
| Speech, muffled | 3 / 5 |
| Speech, audio dropouts | 2 / 5 |
| **Reasoning (clean)** | 3 / 5 |

**What the numbers show:** clean audio passed 4 of 5 scenarios, and every attacked condition passed 3 or fewer. Fan noise, which I expected to be the easiest attack, scored lowest (1 / 5). With 5 scenarios per condition, treat these counts as examples of what the lab surfaces, not as a ranking of the attacks.

## Limitations

Please read these before drawing conclusions.

- **Synthetic speech and simulated noise.** Timbre audio with added noise is not the same as real callers.
- **Small sample.** 10 scenarios (5 speech, 5 reasoning). Results are examples, not statistics.
- **One sample agent tested.** Other agents should work in principle, but this has not been verified.
- **Single-message scenarios.** Each scenario is one caller turn, so multi-turn recovery is not measured.
- **Likely cause only.** Speech-vs-reasoning attribution is a signal, not proof.
- **LLM judge.** The judge can be wrong, so read individual verdicts alongside the transcripts and agent replies.
- **Pipeline, not a single model.** Results reflect the whole pipeline (audio, transcription, agent), not Prisma or any single component alone.
- **Demo agent only.** The sample agent is a simple demo, not a production system.

## Responsible use

All data is synthetic. Do not use real phone numbers, Aadhaar, PAN, bank details or recorded customer calls. Do not point the lab at an agent connected to real customer data.

## Project structure

```
app/                 sample voice agent (FastAPI)
scenarios/           scenario generation, validation, storage
audio/               Timbre calls, audio attacks, Prisma transcription
evaluator/           benchmark runner, judge, scoring
data/benchmarks/     saved scenario suites
data/results/        saved run results
run_crash_test.py    command-line entry point
```

## Acknowledgements

Built with Gnani AI's Timbre and Prisma for the Great Indian AI Internship Challenge. Also uses FastAPI, Whisper, edge-tts and Groq.

## Author

**Vansh Mittal** · [LinkedIn](https://linkedin.com/in/vanshmittal18) · [GitHub](https://github.com/vanshhh18)
