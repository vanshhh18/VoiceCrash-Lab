import os
import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("GNANI_API_KEY")

URL = "https://api.vachana.ai/stt/v3"


def transcribe_audio(audio_file):

    if not API_KEY:
        raise ValueError(
            "GNANI_API_KEY not found in .env"
        )

    files = {
        "audio_file": (
            os.path.basename(audio_file),
            open(audio_file, "rb")
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

    transcript = transcribe_audio(
        "data/test_voice.wav"
    )

    print("\nTranscript:")
    print(transcript)