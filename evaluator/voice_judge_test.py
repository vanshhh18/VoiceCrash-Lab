from evaluator.groq_judge import evaluate_with_groq
from audio.prisma_response_check import transcribe_response


SCENARIO = {
    "id": "scenario_1",
    "type": "ambiguous_request",
    "difficulty": "medium",
    "language": "Hinglish",
    "caller": "Hey, mujhe mera pizza jaldi chahiye. Can you get it here asap?",
    "expected": (
        "The agent should clarify the customer's desired "
        "delivery time or time window instead of asking "
        "for unrelated information."
    )
}

RESPONSE_AUDIO = (
    "data/phase1_scenario1_response.mp3"
)


print("\nSending response audio to Prisma...")

response_transcript = transcribe_response(
    RESPONSE_AUDIO
)

print("\nPrisma Response Transcript:")
print(response_transcript)


print("\nSending result to Groq Judge...")

result = evaluate_with_groq(
    SCENARIO,
    SCENARIO["caller"],
    response_transcript
)

print("\n" + "=" * 50)
print("VOICE CRASH RESULT")
print("=" * 50)

print(f"\nResult: {'PASS' if result['passed'] else 'FAIL'}")
print(f"Category: {result['category']}")
print(f"Severity: {result['severity']}")
print(f"Reason: {result['reason']}")