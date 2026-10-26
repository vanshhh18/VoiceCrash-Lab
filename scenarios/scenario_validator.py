REQUIRED_FIELDS = [
    "id",
    "type",
    "difficulty",
    "language",
    "conditions",
    "caller",
    "expected"
]

VALID_DIFFICULTIES = {
    "easy",
    "medium",
    "hard",
    "expert"
}


def validate_scenario(scenario):
    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in scenario:
            errors.append(f"Missing field: {field}")

    if errors:
        return False, errors

    # Check empty values
    for field in REQUIRED_FIELDS:
        if scenario[field] is None:
            errors.append(f"Empty field: {field}")

    # Check difficulty
    if scenario["difficulty"] not in VALID_DIFFICULTIES:
        errors.append(
            f"Invalid difficulty: {scenario['difficulty']}"
        )

    # Conditions must be a list
    if not isinstance(scenario["conditions"], list):
        errors.append("conditions must be a list")

    # Caller must be text
    if not isinstance(scenario["caller"], str):
        errors.append("caller must be a string")

    # Expected must be text
    if not isinstance(scenario["expected"], str):
        errors.append("expected must be a string")

    if errors:
        return False, errors

    return True, []


def validate_scenarios(scenarios):

    valid = []
    invalid = []

    for scenario in scenarios:

        is_valid, errors = validate_scenario(scenario)

        if is_valid:
            valid.append(scenario)
        else:
            invalid.append({
                "scenario": scenario,
                "errors": errors
            })

    return valid, invalid


if __name__ == "__main__":

    # Test scenario
    test_scenario = {
        "id": 101,
        "type": "billing_inquiry",
        "difficulty": "hard",
        "language": "Hinglish",
        "conditions": ["code_switching"],
        "caller": "Mera bill kitna hai?",
        "expected": "Agent should provide the bill amount."
    }

    is_valid, errors = validate_scenario(test_scenario)

    print("\nScenario validation")

    if is_valid:
        print("VALID")
    else:
        print("INVALID")
        for error in errors:
            print("-", error)