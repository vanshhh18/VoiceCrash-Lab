def build_evaluation_prompt(scenario, transcript, response):

    return f"""
You are evaluating an AI voice agent.

SCENARIO:
Type: {scenario["type"]}
Difficulty: {scenario["difficulty"]}
Language: {scenario["language"]}

CALLER:
{transcript}

EXPECTED BEHAVIOR:
{scenario["expected"]}

AGENT RESPONSE:
{response}

Evaluate whether the agent handled the caller correctly.

Return only this JSON format:

{{
    "passed": true,
    "category": "PASS",
    "severity": "low",
    "reason": "Short explanation"
}}

Possible categories:
- PASS
- STT_FAILURE
- INTENT_MISUNDERSTANDING
- CONTEXT_FAILURE
- CLARIFICATION_FAILURE
- IDENTITY_FAILURE
- EMPATHY_FAILURE
- UNKNOWN_FAILURE

Possible severity:
- low
- medium
- high
"""


def evaluate(scenario, response):

    response = response.lower()
    scenario_type = scenario["type"]

    # Normal Hindi / Hinglish
    if scenario_type in ["normal_hindi", "hinglish"]:

        passed = (
            "reschedule" in response
            or "monday" in response
            or "delivery" in response
        )

        category = (
            "PASS"
            if passed
            else "INTENT_MISUNDERSTANDING"
        )

        reason = (
            "Agent recognized the delivery request."
            if passed
            else "Agent failed to recognize the delivery request."
        )

    # Background noise
    elif scenario_type == "background_noise":

        passed = (
            "reschedule" in response
            or "monday" in response
            or "delivery" in response
        )

        category = (
            "PASS"
            if passed
            else "STT_FAILURE"
        )

        reason = (
            "Agent understood the request despite noisy audio."
            if passed
            else "Agent failed to understand the request after noise."
        )

    # Interruption
    elif scenario_type == "interruption":

        passed = "tuesday" in response

        category = (
            "PASS"
            if passed
            else "CONTEXT_FAILURE"
        )

        reason = (
            "Agent correctly used the final requested date."
            if passed
            else "Agent failed to follow the corrected request."
        )

    # Mumbling
    elif scenario_type == "mumbling":

        clarification_words = [
            "please repeat",
            "could you repeat",
            "clarify",
            "which date",
            "more information",
            "didn't understand",
            "did not understand"
        ]

        passed = any(
            word in response
            for word in clarification_words
        )

        category = (
            "PASS"
            if passed
            else "CLARIFICATION_FAILURE"
        )

        reason = (
            "Agent asked for clarification."
            if passed
            else "Agent should have asked for clarification."
        )

    # Changing request
    elif scenario_type == "changing_request":

        passed = "wednesday" in response

        category = (
            "PASS"
            if passed
            else "CONTEXT_FAILURE"
        )

        reason = (
            "Agent correctly followed the updated request."
            if passed
            else "Agent failed to follow the updated request."
        )

    # Wrong number
    elif scenario_type == "wrong_number":

        identity_words = [
            "confirm",
            "who",
            "wrong number",
            "not rahul",
            "verify",
            "identity"
        ]

        passed = any(
            word in response
            for word in identity_words
        )

        category = (
            "PASS"
            if passed
            else "IDENTITY_FAILURE"
        )

        reason = (
            "Agent attempted to verify the caller's identity."
            if passed
            else "Agent should have verified the caller's identity."
        )

    # Angry caller
    elif scenario_type == "angry_caller":

        empathy_words = [
            "i understand",
            "i can help",
            "let me help",
            "i'll help",
            "sorry about",
            "i apologize",
            "understand your frustration"
        ]

        passed = any(
            word in response
            for word in empathy_words
        )

        category = (
            "PASS"
            if passed
            else "EMPATHY_FAILURE"
        )

        reason = (
            "Agent responded with empathy and offered help."
            if passed
            else "Agent failed to respond appropriately to the angry caller."
        )

    else:

        passed = False
        category = "UNKNOWN_FAILURE"
        reason = "No evaluator rule for this scenario."

    return {
        "passed": passed,
        "category": category,
        "reason": reason
    }