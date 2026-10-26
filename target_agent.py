import os
import requests
from dotenv import load_dotenv

load_dotenv()

TARGET_AGENT_URL = os.getenv(
    "TARGET_AGENT_URL",
    "http://localhost:8000/chat"
)


def call_target_agent(
    transcript,
    target_url=None
):
    url = target_url or TARGET_AGENT_URL

    response = requests.post(
        url,
        params={"message": transcript},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data["response"]


if __name__ == "__main__":
    test_message = "Mujhe apni delivery Monday ko chahiye."

    response = call_target_agent(test_message)

    print("Target Agent Response:")
    print(response)