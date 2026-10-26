import json

from scenarios.scenario_generator import get_scenarios
from app.main import process_message
from evaluator.evaluate import evaluate
from audio.audio_attacks import (
    add_background_noise,
    create_interruption
)
from audio.prisma_stt import transcribe_audio

from target_agent import call_target_agent

from evaluator.groq_judge import evaluate_with_groq


INPUT_AUDIO = None


def prepare_audio(scenario):
    base_audio = scenario["audio_file"]
    conditions = scenario["conditions"]

    if "background_noise" in conditions:
        output = base_audio.replace(".wav", "_noisy.wav")

        add_background_noise(
            base_audio,
            output
        )

        return output

    if "interruption" in conditions:
        output = base_audio.replace(".wav", "_interruption.wav")

        create_interruption(
            base_audio,
            output
        )

        return output

    if "mumbling" in conditions:
        output = base_audio.replace(".wav", "_mumbling.wav")

        add_background_noise(
            base_audio,
            output,
            noise_level=0.20
        )

        return output

    return base_audio

def run_crash_test(scenario, transcript, audio_file):

    response = call_target_agent(transcript)

    result = evaluate_with_groq(
        scenario,
        transcript,
        response
    )

    return {
        "id": scenario["id"],
        "type": scenario["type"],
        "difficulty": scenario["difficulty"],
        "audio_file": audio_file,
        "transcript": transcript,
        "agent_response": response,
        "result": "PASS" if result["passed"] else "FAIL",
        "category": result["category"],
        "severity": result["severity"],
        "reason": result["reason"]
    }


if __name__ == "__main__":

    scenarios = get_scenarios()
    

    results = []
    passed_count = 0

    print("\n" + "=" * 60)
    print("VOICECRASHLAB - AUDIO ATTACK TEST")
    print("=" * 60)

    for scenario in scenarios:

        print("\n" + "-" * 60)
        print(f"Test {scenario['id']}: {scenario['type']}")
        print(f"Conditions: {scenario['conditions']}")

        audio_file = prepare_audio(scenario)

        print(f"Audio file: {audio_file}")

        if (
            "background_noise" in scenario["conditions"]
            or "interruption" in scenario["conditions"]
        ):
            print("[Prisma] Transcribing attack audio...")

            transcript = transcribe_audio(
                audio_file
            )

        else:
            transcript = scenario["caller"]

        result = run_crash_test(
            scenario,
            transcript,
            audio_file
        )

        results.append(result)

        if result["result"] == "PASS":
            passed_count += 1

        print(f"Transcript: {result['transcript']}")
        print(f"Agent: {result['agent_response']}")
        print(f"Result: {result['result']}")
        print(f"Category: {result['category']}")
        print(f"Reason: {result['reason']}")

    total = len(results)
    failed = total - passed_count
    success_rate = (
        (passed_count / total) * 100
        if total > 0
        else 0
    )

    final_results = {
        "total_tests": total,
        "passed": passed_count,
        "failed": failed,
        "success_rate": success_rate,
        "tests": results
    }

    with open(
        "data/results.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            final_results,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 60)
    print("AUDIO ATTACK TEST COMPLETE")
    print("=" * 60)

    print(f"Tests: {total}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {success_rate:.1f}%")
    print("\nResults saved to data/results.json")


