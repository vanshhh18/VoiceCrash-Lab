
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def transcribe_audio(audio_file):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env")

    path = Path(audio_file)

    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")

    model = os.getenv(
        "GROQ_STT_MODEL",
        "whisper-large-v3-turbo",
    )

    client = Groq(
        api_key=api_key,
        timeout=60.0,
        max_retries=1,
    )

    with path.open("rb") as audio:
        result = client.audio.transcriptions.create(
            file=(path.name, audio),
            model=model,
            language="hi",
            response_format="json",
            temperature=0.0,
        )

    return result.text.strip()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(
            'Usage: python -m audio.stt.groq_stt "path/to/audio.wav"'
        )
        raise SystemExit(1)

    print(transcribe_audio(sys.argv[1]))
