import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from scenarios.scenario_validator import validate_scenarios
from scenarios.scenario_storage import (
    save_benchmark,
    find_matching_benchmark,
    get_benchmark_id,
)

load_dotenv()

BENCHMARK_DIR = Path("data/benchmarks")

def _get_scenario_llm():
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is missing. Add it to .env before generating scenarios.")
    return ChatGroq(
        model=os.getenv("GROQ_SCENARIO_MODEL", os.getenv("GROQ_JUDGE_MODEL", "openai/gpt-oss-120b")),
        temperature=0.7,
        api_key=os.getenv("GROQ_API_KEY"),
    )


def generate_adversarial_scenarios(
    agent_role,
    business_context,
    supported_tasks,
    language="Hinglish",
    count=5,
    test_track=None,
    reuse_existing=False,
    _save=True,
):
    if test_track not in {None, "speech", "reasoning"}:
        raise ValueError(
            "test_track must be None, 'speech', or 'reasoning'"
        )
    """
    Generate and validate adversarial scenarios, save valid scenarios,
    and return (valid_scenarios, benchmark_file_path).

    If reuse_existing=True and a matching benchmark exists, its scenarios
    and path are returned without generating or overwriting anything.
    """
    if reuse_existing and test_track is None:
        matching = find_matching_benchmark(
            agent_role,
            business_context,
            language,
        )

        if matching:
            benchmark_id = matching.get(
                "benchmark_id",
                get_benchmark_id(agent_role),
            )
            benchmark_file = BENCHMARK_DIR / f"{benchmark_id}.json"

            print(f"Reusing benchmark: {benchmark_id}")
            print(f"File: {benchmark_file}")
            return matching.get("scenarios", []), str(benchmark_file)

    tasks = ", ".join(supported_tasks)
    if test_track is None:
        scenarios_by_track = {}

        for track in ("speech", "reasoning"):
            valid, _ = generate_adversarial_scenarios(
                agent_role=agent_role,
                business_context=business_context,
                supported_tasks=supported_tasks,
                language=language,
                count=count,
                test_track=track,
                reuse_existing=False,
                _save=False,
            )

            scenarios_by_track[track] = valid

        if not scenarios_by_track["speech"] or not scenarios_by_track["reasoning"]:
            print("Benchmark not saved: both tracks need valid scenarios.")
            return scenarios_by_track, None

        benchmark_file = save_benchmark(
            agent_role=agent_role,
            business_context=business_context,
            supported_tasks=supported_tasks,
            language=language,
            scenarios=scenarios_by_track,
        )

        return scenarios_by_track, str(benchmark_file)

    if _save:
        raise ValueError(
            "Generate both tracks by calling without test_track."
        )

    
    prompt = f"""
You are an expert adversarial test designer for AI agents.

Generate exactly {count} DISTINCT scenarios for the requested test track.

TARGET AGENT
Role: {agent_role}

Business context:
{business_context}

Supported tasks:
{tasks}

Language: {language}

TEST TRACK: {test_track}

TRACK SEPARATION (STRICT)

The test track will be either "speech" or "reasoning".
Generate scenarios ONLY for the selected track. Never mix speech robustness
tests with hard reasoning tests in the same generation batch.

TRACK A: SPEECH
When test_track is "speech":

- Generate EASY, clear, realistic customer-call scenarios.
- Each scenario must have one straightforward underlying intent.
- Use short, natural caller messages that are easy to understand before
  audio distortions are applied.
- Do not introduce complex ambiguity, multi-step reasoning, conflicting
  instructions, or tricky context-retention requirements.
- Use simple requests relevant to the supplied role, business context,
  and supported tasks.
- Keep the original caller message suitable for testing speech recognition
  under noise, phone-line distortion, audio dropouts, cutoff, and other
  existing audio attacks.
- Do not describe or simulate audio attacks in the caller message itself.
  The audio attack pipeline applies those transformations separately.
- Do not create audio files or modify the attack pipeline here.

The purpose of speech scenarios is to measure whether the system can
recognize and handle simple spoken requests under degraded audio conditions.

TRACK B: REASONING
When test_track is "reasoning":

- Generate HARD or EXPERT scenarios requiring contextual reasoning.
- Combine 2–3 interacting challenges where appropriate.
- Test context retention, changing requests, ambiguity resolution,
  contradictory details, self-correction, indirect references, relevant
  versus irrelevant information, and safe decision-making.
- Include both cases requiring clarification and cases where the agent
  should act directly without unnecessary questions.
- Include cases where the agent must retain the latest confirmed instruction,
  recover from a misunderstanding, or explain a capability limitation.
- Keep messages natural and solvable. Avoid artificial riddles and
  contradictions with no defensible resolution.
- Do not make every scenario depend on dates, numbers, or clarification.
- Difficulty must come from reasoning, not message length or audio noise.

COMMON RULES

1. Make every scenario specific to the supplied role, business context,
   and supported tasks. Do not hardcode rules for any particular industry.

2. Never invent unsupported tasks. If a request exceeds the agent's
   capabilities, test whether the agent explains the limitation or offers
   a valid alternative.

3. Use natural {language} conversation, including appropriate Hindi,
   English, or Hinglish code-switching when suitable.

4. Use fictional information only.

5. Each scenario must have one defensible underlying intent and a clear,
   observable expected outcome.

6. Expected behavior must describe actions and outcomes, not a fixed
   sentence. Accept natural wording variations when the intent is satisfied.

7. Respect actual agent capabilities. Never expect unavailable private
   information, nonexistent tools, or unconfirmed actions to be completed.
   The agent must not claim an action succeeded without evidence.

8. Make scenarios meaningfully different. Do not create near-duplicates
   by changing only names, dates, or amounts.

9. Conditions must describe the challenge and potential failure mode.

10. Expected must state:
    - the caller's underlying goal,
    - relevant and ambiguous information,
    - whether clarification is necessary,
    - observable success criteria,
    - applicable capability and safety constraints.

11. Choose a meaningful type label, such as:
    simple_request, intent_recognition, context_retention,
    changing_request, ambiguity, contradiction, self_correction,
    incomplete_information, code_switching, distraction,
    ASR_error, emotional_pressure, capability_boundary.

OUTPUT REQUIREMENTS

Return ONLY a valid JSON array. Do not include Markdown or explanations.

Generate exactly {count} items. IDs must be scenario_1, scenario_2,
and so on, with no missing or duplicate IDs.

Every item must contain exactly these fields:
{{
  "id": "scenario_1",
  "type": "scenario_type",
  "difficulty": "easy|medium|hard|expert",
  "language": "{language}",
  "conditions": ["specific challenge", "potential failure mode"],
  "caller": "the exact caller message",
  "expected": "underlying intent, relevant facts, clarification
  requirements, success criteria, and capability limits"
}}

Difficulty rules:
- Speech track: every scenario MUST be "easy".
- Reasoning track: every scenario MUST be "hard" or "expert".

Ensure the JSON is syntactically valid, every field has the correct type,
and exactly {count} distinct scenarios are returned.
"""
    response = _get_scenario_llm().invoke(prompt)
    content = response.content.strip()

    # Remove Markdown fences if the model adds them.
    content = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        content,
        flags=re.IGNORECASE,
    ).strip()

    try:
        scenarios = json.loads(content)
    except json.JSONDecodeError as exc:
        print(f"Groq returned invalid JSON: {exc}")
        print(content)
        return [], None

    # if not isinstance(scenarios, list):
    #     print("Invalid response: expected a JSON array.")
    #     return [], None

    #temporary
    if not isinstance(scenarios, list):
        print("Invalid response: expected a JSON array.")
        print("Actual response type:", type(scenarios).__name__)
        print("Actual response content:")
        print(json.dumps(scenarios, indent=2, ensure_ascii=False))
        return [], None

    # Normalize nested scenario wrappers if present.
    normalized = []
    for item in scenarios:
        if isinstance(item, dict) and "scenario" in item:
            item = item["scenario"]
        if isinstance(item, dict):
            normalized.append(item)

    scenarios = normalized[:count]

    # Assign consistent IDs and normalize conditions/language.
    for index, scenario in enumerate(scenarios, start=1):
        scenario["id"] = f"scenario_{index}"

        if isinstance(scenario.get("conditions"), str):
            scenario["conditions"] = [scenario["conditions"]]

        scenario["language"] = language

    if len(scenarios) != count:
        print(
            f"Warning: requested {count} scenarios, "
            f"received {len(scenarios)}."
        )

    valid, invalid = validate_scenarios(scenarios)

    print(f"Generated: {len(scenarios)}")
    print(f"Valid: {len(valid)}")
    print(f"Invalid: {len(invalid)}")

    for item in invalid:
        rejected = item.get("scenario", {})
        print(f"\nRejected {rejected.get('id', 'unknown')}:")
        for error in item.get("errors", []):
            print(f"- {error}")

    if not valid:
        print("No valid scenarios to save.")
        return [], None

    
    if not _save:
        return valid, None

    return valid, None



if __name__ == "__main__":
    agent_role = "Banking Customer Support Agent"

    business_context = (
        "A banking platform that handles customer inquiries "
        "and account management."
    )

    supported_tasks = [
        "check account balance",
        "transfer money",
        "report lost card",
        "apply for loan",
    ]
    

    generated, benchmark_file = generate_adversarial_scenarios(
        agent_role=agent_role,
        business_context=business_context,
        supported_tasks=supported_tasks,
        language="Hinglish",
        count=5,
        reuse_existing=False,
    )

    if not generated or not benchmark_file:
        raise SystemExit(1)

    print(json.dumps(generated, indent=2, ensure_ascii=False))
    print(f"\nBenchmark ready: {benchmark_file}")
