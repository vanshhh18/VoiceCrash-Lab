import json


CATEGORY_SCORES = {
    "PASS": 100,
    "STT_FAILURE": 40,
    "INTENT_MISUNDERSTANDING": 30,
    "CONTEXT_FAILURE": 30,
    "CLARIFICATION_FAILURE": 30,
    "IDENTITY_FAILURE": 30,
    "EMPATHY_FAILURE": 30,
    "UNKNOWN_FAILURE": 20
}


def calculate_crash_score(results):
    tests = results["tests"]

    if not tests:
        return 0

    scores = []

    for test in tests:
        category = test["category"]
        score = CATEGORY_SCORES.get(category, 20)
        scores.append(score)

    return round(sum(scores) / len(scores), 1)


if __name__ == "__main__":

    with open(
        "data/results.json",
        "r",
        encoding="utf-8"
    ) as file:
        results = json.load(file)

    score = calculate_crash_score(results)

    print("\n" + "=" * 50)
    print("VOICECRASHLAB CRASH SCORE")
    print("=" * 50)

    print(f"\nCrash Score: {score}/100")