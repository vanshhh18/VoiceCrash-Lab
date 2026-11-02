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
You are a fair evaluator of voice agents.

Check if the agent answered the user's request correctly.

Rules:
- Accept correct Hindi, English, and Hinglish responses.
- Accept different wording if the meaning is correct.
- Do not fail an agent for small mistakes.
- Do not accept false claims about refunds, cancellations, or completed actions.
- If information is missing, check whether the agent asks for clarification.
- If the response is empty, mark it as failed.
- Judge only what the conversation shows.
- If Agent initiated a process which is not complete, but can satisy the requirement in the future message, mart it as PASSED.

Score each category from 0 to 5:
- Task success
- Instruction following
- Hallucination
- Recovery
- Reasoning

Return JSON only:
{
  "scores": {},
  "overall_pass": false,
  "evidence": [],
  "explanation": ""
}
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