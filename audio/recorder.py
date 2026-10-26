import sounddevice as sd
from scipy.io.wavfile import write


SAMPLE_RATE = 16000
DURATION = 6


def record_audio(output_file):
    print("Recording...")
    print("Speak now!")

    recording = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16"
    )

    sd.wait()

    write(
        output_file,
        SAMPLE_RATE,
        recording
    )

    print(f"Recording saved to {output_file}")


if __name__ == "__main__":
    record_audio("data/test_voice.wav")