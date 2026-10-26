import json
from collections import Counter


with open("data/results.json", "r", encoding="utf-8") as file:
    data = json.load(file)


tests = data["tests"]

failures = [
    test
    for test in tests
    if test["result"] == "FAIL"
]


failure_categories = Counter(
    test["category"]
    for test in failures
)


print("\n" + "=" * 50)
print("VOICECRASHLAB FAILURE ANALYSIS")
print("=" * 50)

print(f"\nTotal tests: {len(tests)}")
print(f"Passed: {data['passed']}")
print(f"Failed: {data['failed']}")
print(f"Success rate: {data['success_rate']:.1f}%")

print("\nFAILURES BY CATEGORY")
print("-" * 30)

for category, count in failure_categories.most_common():
    print(f"{category}: {count}")


print("\nDETAILED FAILURES")
print("-" * 30)

for test in failures:

    print(f"\nTest {test['id']}")
    print(f"Type: {test['type']}")
    print(f"Difficulty: {test['difficulty']}")
    print(f"Agent: {test['agent_response']}")
    print(f"Category: {test['category']}")
    print(f"Reason: {test['reason']}")