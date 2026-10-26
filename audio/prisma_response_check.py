import os
import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("GNANI_API_KEY")

URL = "https://api.vachana.ai/stt/v3"

AUDIO_FILE = "data/phase1_agent_response.mp3"


def transcribe_response(audio_file):

    if not API_KEY:
        raise ValueError(
            "GNANI_API_KEY not found in .env"
        )

    with open(audio_file, "rb") as audio:

        files = {
            "audio_file": (
                os.path.basename(audio_file),
                audio
            )
        }

        data = {
            "language_code": "hi-IN",
            "preferred_language": "hi-IN",
            "format": "transcribe",
            "itn_native_numerals": "true"
        }

        headers = {
            "X-API-Key-ID": API_KEY
        }

        response = requests.post(
            URL,
            data=data,
            files=files,
            headers=headers
        )

    response.raise_for_status()

    result = response.json()

    return result["transcript"]


if __name__ == "__main__":

    print("Sending agent response audio to Prisma...")

    transcript = transcribe_response(
        AUDIO_FILE
    )

    print("\nPrisma Response Transcript:")
    print(transcript)