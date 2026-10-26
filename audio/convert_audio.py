from pydub import AudioSegment

audio = AudioSegment.from_mp3(
    "data/phase1_clean.mp3"
)

audio = audio.set_frame_rate(16000)
audio = audio.set_channels(1)

audio.export(
    "data/phase1_clean.wav",
    format="wav"
)

print("WAV created successfully.")