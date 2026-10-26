SCENARIOS = [
    {
        "id": 1,
        "type": "normal_hindi",
        "difficulty": "easy",
        "language": "Hindi",
        "conditions": [],
        "caller": "Mujhe apni delivery Monday ko chahiye.",
        "audio_file": "data/scenario_1.wav",
        "expected": "Agent should understand that the customer wants delivery on Monday."
    },
    {
        "id": 2,
        "type": "hinglish",
        "difficulty": "medium",
        "language": "Hinglish",
        "conditions": ["code_switching"],
        "caller": "Bhai, meri delivery Monday ko reschedule kar sakte ho?",
        "audio_file": "data/scenario_2.wav",
        "expected": "Agent should understand the Hinglish request."
    },
    {
        "id": 3,
        "type": "background_noise",
        "difficulty": "hard",
        "language": "Hindi",
        "conditions": ["background_noise"],
        "caller": "Meri delivery Monday ko kar do.",
        "audio_file": "data/scenario_3.wav",
        "expected": "Agent should understand the request despite background noise."
    },
    {
        "id": 4,
        "type": "interruption",
        "difficulty": "hard",
        "language": "Hindi",
        "conditions": ["interruption"],
        "caller": "Actually meri delivery Monday ko... nahi, Tuesday ko kar do.",
        "audio_file": "data/scenario_4.wav",
        "expected": "Agent should use the final date: Tuesday."
    },
    {
        "id": 5,
        "type": "mumbling",
        "difficulty": "hard",
        "language": "Hindi",
        "conditions": ["mumbling"],
        "caller": "Umm... woh... delivery... Monday...",
        "audio_file": "data/scenario_5.wav",
        "expected": "Agent should ask for clarification."
    },
    {
        "id": 6,
        "type": "changing_request",
        "difficulty": "hard",
        "language": "Hinglish",
        "conditions": ["request_change"],
        "caller": "Delivery Monday ko chahiye. Actually nahi, Wednesday better hai.",
        "audio_file": "data/scenario_6.wav",
        "expected": "Agent should use Wednesday."
    },
    {
        "id": 7,
        "type": "wrong_number",
        "difficulty": "medium",
        "language": "Hindi",
        "conditions": ["identity_confusion"],
        "caller": "Hello, kya yahan Rahul bol raha hai?",
        "audio_file": "data/scenario_7.wav",
        "expected": "Agent should verify identity."
    },
    {
        "id": 8,
        "type": "angry_caller",
        "difficulty": "hard",
        "language": "Hindi",
        "conditions": ["emotional_pressure"],
        "caller": "Teen baar delivery cancel ho chuki hai, mujhe abhi solution chahiye!",
        "audio_file": "data/scenario_8.wav",
        "expected": "Agent should remain calm and help the customer."
    }
]


def get_scenarios():
    return SCENARIOS


if __name__ == "__main__":

    for scenario in SCENARIOS:

        print("\n" + "=" * 50)

        print(f"TEST {scenario['id']}")
        print(f"Type: {scenario['type']}")
        print(f"Difficulty: {scenario['difficulty']}")
        print(f"Language: {scenario['language']}")
        print(f"Conditions: {scenario['conditions']}")
        print(f"Caller: {scenario['caller']}")
        print(f"Expected: {scenario['expected']}")