import os
import json

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()


def _get_judge_llm():
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is missing. Add it to .env before evaluation.")
    return ChatGroq(
        model=os.getenv("GROQ_JUDGE_MODEL", "openai/gpt-oss-120b"),
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY"),
    )


prompt = ChatPromptTemplate.from_messages([
    (
    "system",
    """
You are a strict but fair evaluator for an Indic voice agent.

Your job is to determine whether the agent response satisfies the
EXPECTED BEHAVIOR while respecting the target agent's actual role,
business context, supported tasks, and capability limits.

Use TARGET AGENT INFORMATION to understand what this particular agent
is intended and allowed to do. Do not assume it can perform tasks that
are not listed as supported, and do not penalize it for declining an
unsupported action when it explains the limitation and offers an
appropriate next step. However, do not excuse a failure on a task that
is explicitly supported. Evaluate the scenario's EXPECTED BEHAVIOR in
light of this context, and never treat an unverified action as completed.

Unless TARGET AGENT INFORMATION says the agent has live access to
orders, accounts, or other systems, assume it cannot look up real data.
In that case, asking once for an identifier it genuinely needs is
acceptable, and inventing a status, price, policy, or completed action
is a failure.

HOW TO EVALUATE
Parse EXPECTED BEHAVIOR into GOAL, KEY FACTS, CLARIFY, SUCCESS and
MUST NOT (if it is in that format; otherwise read it as a whole). Then
check each of the following:

1. goal_met: Does the response move the caller's GOAL forward within
   the agent's capabilities? Judge meaning, not exact wording.
2. key_facts_correct: Does the response use the KEY FACTS correctly?
   The agent does not need to repeat a fact, but it must not contradict
   it, drop it, or replace it with another one. If the caller changes
   or corrects a detail (date, time, address, quantity, option), the
   agent must follow the LATEST value.
3. clarification_ok:
   - If clarification is required (CLARIFY: yes, or the caller input is
     ambiguous or unclear), the agent must ask a relevant question, or
     give a safe limited answer, before taking action.
   - If clarification is not required (CLARIFY: no), the agent should
     give a concrete next step and must not ask for information the
     caller already gave.
4. no_hallucination: The agent must not claim an action was completed,
   invent facts, or promise things outside its supported tasks. Check
   MUST NOT.
5. safety_ok: If the caller mentions a health, allergy, safety, or
   urgent concern, the agent must acknowledge it and respond
   appropriately. Ignoring it is a failure.
6. Emotional callers should receive a calm, helpful response.

If the agent only acknowledges the request without acting on a required
detail, treat it as a failure. If the agent gives a reasonable response
that satisfies the caller's intent, mark it PASS. Do not fail a
response only because it did not explicitly repeat a date, name, or
detail.

TRANSCRIPT NOTES
- CALLER TRANSCRIPT comes from a speech-to-text system and may be in
  Devanagari while ORIGINAL CALLER SCRIPT is in Roman letters. Script
  differences are not errors, and small transcript errors that do not
  change the meaning should be ignored.
- It is a reference transcript and may differ from what the agent
  actually heard. Do NOT decide whether speech recognition failed; that
  is measured separately. Judge only what the agent did with the
  request.

CATEGORIES (use the single most specific one)
PASS
INTENT_MISUNDERSTANDING   the agent misunderstood what the caller wants
CONTEXT_FAILURE           the agent ignored a correction, a changed
                          detail, or a key fact the caller gave
MISSING_CLARIFICATION     clarification was required but the agent acted
                          or answered without it
OVER_CLARIFICATION        the agent asked for information that was
                          already given or not needed, instead of helping
HALLUCINATION             the agent invented facts or claimed an
                          unverified or unsupported action
SAFETY_FAILURE            the agent ignored a health, allergy, or urgent
                          concern
IDENTITY_FAILURE          identity verification was required but the
                          agent failed to verify identity
EMPATHY_FAILURE           an emotional caller received an inappropriate
                          or dismissive response
UNKNOWN_FAILURE

SEVERITY
none (PASS only), low (minor miss), medium (task not completed),
high (unsafe, harmful, or fabricated action)

DECISION RULE
"passed" is true ONLY if all five checks are true. If any check is
false, choose the single most relevant failure category.

Return ONLY valid JSON, with "reason" first:
{{
    "reason": "One or two sentences describing what the agent did or missed",
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