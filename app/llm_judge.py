import json
import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DIMENSIONS = [
    "task_success",
    "instruction_adherence",
    "hallucination",
    "recovery",
    "reasoning_correctness",
]


JUDGE_SYSTEM_PROMPT = """
You are an independent evaluator for a black-box voice-agent benchmark.

Evaluate only the target agent's observable response transcript.
Do not assume access to the target agent's internal reasoning, tools,
database, or actual actions.

Use the scenario's expected behavior and success criteria as evaluation
requirements. Do not treat an example response as the only acceptable
wording. Accept semantically equivalent responses, including natural
Hindi and Hinglish responses.

Evaluation rules:
1. Do not award success for an action merely because the agent claims it
   performed that action.
2. Do not assume a delivery status, cancellation, or refund was actually
   verified unless the transcript provides appropriate evidence.
3. If required information is missing, check whether the agent asks for
   the necessary clarification.
4. Do not penalize the agent for honestly explaining a capability limit.
5. For reasoning scenarios, assess whether the response addresses all
   relevant parts of the request and handles changing requests correctly.
6. Evaluate recovery only from observable conversational evidence.
7. If the transcript is empty or unavailable, do not assume success.
8. Do not assume an attack caused a failure just because an attack was
   applied. Judge the observed response.
9. Treat unsupported factual claims as potential hallucinations.
10. Be conservative when evidence is insufficient.

Score each dimension from 0 to 5:
0 = complete failure or seriously incorrect
1 = major failure
2 = partially correct, with significant omissions
3 = mostly correct, with some gaps
4 = correct, with minor issues
5 = fully meets the applicable requirements

Return valid JSON only, using this structure:
{
  "scores": {
    "task_success": 0,
    "instruction_adherence": 0,
    "hallucination": 0,
    "recovery": 0,
    "reasoning_correctness": 0
  },
  "overall_pass": false,
  "evidence": ["short transcript-based evidence"],
  "explanation": "brief explanation",
  "uncertainties": ["what could not be verified"]
}

Use integer scores from 0 to 5.
Set overall_pass to true only when the response adequately meets the
scenario's applicable success criteria and does not contain a critical
failure or unsupported consequential claim.
"""


def _validate_result(result: dict[str, Any]) -> dict[str, Any]:
    scores = result.get("scores")

    if not isinstance(scores, dict):
        raise ValueError("Judge result must contain a scores object.")

    for dimension in DIMENSIONS:
        score = scores.get(dimension)

        if isinstance(score, bool) or not isinstance(score, int):
            raise ValueError(
                f"Score for {dimension} must be an integer."
            )

        if not 0 <= score <= 5:
            raise ValueError(
                f"Score for {dimension} must be between 0 and 5."
            )

    if not isinstance(result.get("overall_pass"), bool):
        raise ValueError("overall_pass must be a boolean.")

    if not isinstance(result.get("evidence"), list):
        raise ValueError("evidence must be a list.")

    if not isinstance(result.get("explanation"), str):
        raise ValueError("explanation must be a string.")

    if not isinstance(result.get("uncertainties"), list):
        raise ValueError("uncertainties must be a list.")

    return result


def judge_transcript(
    scenario: dict[str, Any],
    transcript: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Evaluate one observable target-agent transcript against one scenario.

    The target agent's internals and actual tool execution are not available
    to the judge.
    """
    if not isinstance(scenario, dict):
        raise TypeError("scenario must be a dictionary.")

    if not isinstance(transcript, str):
        raise TypeError("transcript must be a string.")

    if not scenario.get("expected"):
        raise ValueError("Scenario must contain expected behavior.")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env.")

    model = model or os.getenv("GROQ_JUDGE_MODEL")
    if not model:
        raise ValueError(
            "Set GROQ_JUDGE_MODEL in .env to a supported Groq chat model."
        )

    evaluation_input = {
        "scenario": {
            "id": scenario.get("id"),
            "type": scenario.get("type"),
            "difficulty": scenario.get("difficulty"),
            "language": scenario.get("language"),
            "conditions": scenario.get("conditions", []),
            "caller": scenario.get("caller"),
            "expected": scenario.get("expected"),
        },
        "target_response_transcript": transcript,
    }

    client = Groq(api_key=api_key, timeout=60.0, max_retries=1)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": JUDGE_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    evaluation_input,
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("Groq judge returned an empty response.")

    result = json.loads(content)
    return _validate_result(result)