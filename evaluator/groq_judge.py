import json
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()


@lru_cache(maxsize=1)
def get_judge_llm() -> ChatGroq:
    """Build the judge LLM once and reuse it across calls (adds explicit timeout)."""
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is missing. Add it to .env before evaluation.")
    return ChatGroq(
        model=os.getenv("GROQ_JUDGE_MODEL", "openai/gpt-oss-120b"),
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
        timeout=60.0,
        max_retries=1,
    )


def _get_judge_llm():
    return get_judge_llm()


prompt = ChatPromptTemplate.from_messages([
    (
    "system",
    """
You are a chill and fair voice agent evaluator.

Check if the agent gave a helpful answer to the caller.

Rules:
- Accept natural Hindi, English, and Hinglish.
- Accept different wording if the meaning is correct.
- Don't fail for small mistakes.
- Don't expect perfect answers.
- If the agent needs more information, asking a question is fine.
- If the agent cannot do something, explaining the limitation is fine.
- Don't accept made-up facts or fake claims about completed actions.
- Be understanding with upset callers.
- Ignore small speech-to-text mistakes.
- Judge only the agent's response.
- If the agent initiated a process which is not complete, but can satisfy the requirement in the future message, mark it as PASSED.

Choose a category:
PASS, INTENT_MISUNDERSTANDING, CONTEXT_FAILURE,
MISSING_CLARIFICATION, OVER_CLARIFICATION, HALLUCINATION,
SAFETY_FAILURE, IDENTITY_FAILURE, EMPATHY_FAILURE,
UNKNOWN_FAILURE.

Severity:
none = PASS
low = small mistake
medium = request not handled properly
high = harmful response or fake action

Be generous when the response is reasonable.
Set passed to true if the caller's main need is handled
without any serious mistake.

Return valid JSON only:
{{
  "reason": "Short explanation",
  "checks": {{
    "goal_met": true,
    "key_facts_correct": true,
    "clarification_ok": true,
    "no_hallucination": true,
    "safety_ok": true
}},
  "passed": true,
  "category": "PASS",
  "severity": "none"
}}
"""
),
    (
        "human",
        """
TARGET AGENT INFORMATION:
Role: {agent_role}
Business context: {business_context}
Supported tasks:
{supported_tasks}
Agent language: {agent_language}

SCENARIO TYPE:
{scenario_type}

DIFFICULTY:
{difficulty}

LANGUAGE:
{language}

ORIGINAL CALLER SCRIPT:
{original_text}

CALLER TRANSCRIPT (reference STT, not necessarily what the agent heard):
{transcript}

EXPECTED BEHAVIOR:
{expected}

AGENT RESPONSE:
{response}
"""
    )
])


def evaluate_with_groq(
    scenario,
    transcript,
    response,
    original_text=None,
    agent_info=None,
):

    # Explicit argument takes priority; environment values support the Streamlit workflow.
    agent_info = agent_info or scenario.get("agent_info", {}) or {}
    if not isinstance(agent_info, dict):
        agent_info = {}

    supported_tasks = agent_info.get("supported_tasks", os.getenv("VOICECRASHLAB_SUPPORTED_TASKS", ""))
    if isinstance(supported_tasks, (list, tuple, set)):
        supported_tasks = "\n".join(str(task) for task in supported_tasks)

    chain = prompt | _get_judge_llm()

    result = chain.invoke({
        "agent_role": agent_info.get("agent_role", os.getenv("VOICECRASHLAB_AGENT_ROLE", "Not provided")),
        "business_context": agent_info.get("business_context", os.getenv("VOICECRASHLAB_BUSINESS_CONTEXT", "Not provided")),
        "supported_tasks": supported_tasks or "Not provided",
        "agent_language": agent_info.get("language", os.getenv("VOICECRASHLAB_AGENT_LANGUAGE", scenario.get("language", "Not provided"))),
        "scenario_type": scenario["type"],
        "difficulty": scenario["difficulty"],
        "language": scenario["language"],
        "transcript": transcript,
        "expected": scenario["expected"],
        "response": response,
        "original_text": original_text or scenario.get("caller", ""),
    })

    return json.loads(result.content)


if __name__ == "__main__":

    test_cases = [

        {
            "name": "Interruption",
            "scenario": {
                "type": "interruption",
                "difficulty": "hard",
                "language": "Hindi",
                "expected": "Agent should use the final date: Tuesday."
            },
            "transcript": "Actually meri delivery Monday ko... nahi, Tuesday ko kar do.",
            "response": "Sorry, I did not understand your request."
        },

        {
            "name": "Mumbling",
            "scenario": {
                "type": "mumbling",
                "difficulty": "hard",
                "language": "Hindi",
                "expected": "Agent should ask for clarification."
            },
            "transcript": "Umm... woh... delivery... Monday...",
            "response": "Sure, I can help you reschedule your delivery."
        },

        {
            "name": "Angry Caller",
            "scenario": {
                "type": "angry_caller",
                "difficulty": "hard",
                "language": "Hindi",
                "expected": "Agent should remain calm and help the customer."
            },
            "transcript": "Teen baar delivery cancel ho chuki hai, mujhe abhi solution chahiye!",
            "response": "Sorry, I did not understand your request."
        },

        {
            "name": "Correct Response",
            "scenario": {
                "type": "normal_hindi",
                "difficulty": "easy",
                "language": "Hindi",
                "expected": "Agent should understand that the customer wants delivery on Monday."
            },
            "transcript": "Mujhe apni delivery Monday ko chahiye.",
            "response": "Sure, I can help you reschedule your delivery."
        }
    ]

    for test in test_cases:

        print("\n" + "=" * 60)
        print(test["name"])
        print("=" * 60)

        result = evaluate_with_groq(
            test["scenario"],
            test["transcript"],
            test["response"]
        )

        print(json.dumps(result, indent=4))