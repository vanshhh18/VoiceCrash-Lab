
import os


def transcribe_audio(audio_file):
    provider = os.getenv(
        "STT_PROVIDER", "groq"
    ).strip().lower()

    if provider == "groq":
        from audio.stt.groq_stt import transcribe_audio as transcribe
    elif provider == "whisper":
        from audio.stt.whisper_stt import transcribe_audio as transcribe
    elif provider == "prisma":
        from audio.prisma_stt import transcribe_audio as transcribe
    else:
        raise ValueError(
            f"Unknown STT_PROVIDER: {provider}"
        )

    return transcribe(audio_file)
