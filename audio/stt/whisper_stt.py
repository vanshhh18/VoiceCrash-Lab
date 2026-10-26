
import os
from functools import lru_cache

from faster_whisper import WhisperModel


@lru_cache(maxsize=1)
def get_model():
    model_size = os.getenv("WHISPER_MODEL", "small")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    return WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
    )


def transcribe_audio(audio_file):
    if not os.path.isfile(audio_file):
        raise FileNotFoundError(
            f"Audio file not found: {audio_file}"
        )

    model = get_model()

    segments, info = model.transcribe(
        audio_file,
        language="hi",
        vad_filter=True,
    )

    transcript = " ".join(
        segment.text.strip()
        for segment in segments
        if segment.text.strip()
    ).strip()

    return transcript


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python -m audio.stt.whisper_stt "
            "path/to/audio.wav"
        )
        raise SystemExit(1)

    print(transcribe_audio(sys.argv[1]))
