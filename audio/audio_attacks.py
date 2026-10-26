from pathlib import Path

import numpy as np
from pydub import AudioSegment
from scipy.signal import butter, sosfilt


AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}
BACKGROUND_TYPES = {
    "traffic": {"snr_db": -2},
    "fan": {"snr_db": -10},
    "crowd": {"snr_db": 2},
}


def load_audio(path):
    """Load audio and standardize it to mono, 16 kHz, 16-bit PCM."""
    return (
        AudioSegment.from_file(path)
        .set_channels(1)
        .set_frame_rate(16000)
        .set_sample_width(2)
    )


def save_audio(audio, output_file):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    audio.export(output_file, format=output_file.suffix.lstrip(".") or "wav")
    print(f"Saved: {output_file}")
    return output_file


def _samples(audio):
    return np.asarray(audio.get_array_of_samples(), dtype=np.float32)


def _mix_at_snr(speech, background, snr_db, seed=42):
    """Mix background audio at an approximate speech-to-noise ratio."""
    speech = speech.set_channels(1).set_frame_rate(16000).set_sample_width(2)
    background = (
        background.set_channels(1)
        .set_frame_rate(16000)
        .set_sample_width(2)
    )

    speech_samples = _samples(speech)
    bg_samples = _samples(background)

    if len(bg_samples) == 0:
        raise ValueError("Background audio is empty.")
    if len(speech_samples) == 0:
        raise ValueError("Speech audio is empty.")

    # Repeat a short ambience recording so it covers the entire utterance.
    if len(bg_samples) < len(speech_samples):
        repeats = int(np.ceil(len(speech_samples) / len(bg_samples)))
        bg_samples = np.tile(bg_samples, repeats)

    # Choose a deterministic random crop to avoid always starting at the same point.
    rng = np.random.default_rng(seed)
    max_start = len(bg_samples) - len(speech_samples)
    start = int(rng.integers(0, max_start + 1)) if max_start > 0 else 0
    bg_samples = bg_samples[start:start + len(speech_samples)].copy()

    speech_rms = np.sqrt(np.mean(speech_samples ** 2)) + 1e-8
    bg_rms = np.sqrt(np.mean(bg_samples ** 2)) + 1e-8
    target_bg_rms = speech_rms / (10 ** (snr_db / 20))
    mixed = speech_samples + bg_samples * (target_bg_rms / bg_rms)

    # Prevent clipping while preserving the relative speech/background balance.
    peak = float(np.max(np.abs(mixed))) if len(mixed) else 0.0
    if peak > 32767:
        mixed *= 32767 / peak

    mixed = np.clip(mixed, -32768, 32767).astype(np.int16)
    return speech._spawn(mixed.tobytes())


def add_background_noise(input_file, output_file, noise_db=10, seed=42):
    """Legacy white-noise helper; retained for compatibility."""
    audio = load_audio(input_file)
    samples = _samples(audio)
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, len(samples)).astype(np.float32)

    signal_rms = np.sqrt(np.mean(samples ** 2)) + 1e-8
    noise_rms = np.sqrt(np.mean(noise ** 2)) + 1e-8
    target_noise_rms = signal_rms / (10 ** (noise_db / 20))
    mixed = samples + noise * (target_noise_rms / noise_rms)

    peak = float(np.max(np.abs(mixed))) if len(mixed) else 0.0
    if peak > 32767:
        mixed *= 32767 / peak

    mixed = np.clip(mixed, -32768, 32767).astype(np.int16)
    return save_audio(audio._spawn(mixed.tobytes()), output_file)


def add_environment_noise(input_file, noise_file, output_file, snr_db, seed=42):
    """Mix a real traffic/fan/crowd recording underneath the caller's speech."""
    speech = load_audio(input_file)
    background = load_audio(noise_file)
    mixed = _mix_at_snr(speech, background, snr_db=snr_db, seed=seed)
    return save_audio(mixed, output_file)


def add_phone_line(input_file, output_file):
    """Simulate a narrow-band phone channel (approximately 300–3400 Hz)."""
    audio = load_audio(input_file)
    samples = _samples(audio)

    sos = butter(
        4,
        [400, 3000],
        btype="bandpass",
        fs=audio.frame_rate,
        output="sos",
    )
    filtered = sosfilt(sos, samples)
    filtered = np.clip(filtered, -32768, 32767).astype(np.int16)

    # Downsample then return to 16 kHz so the exported dataset has a consistent rate.
    filtered_audio = audio._spawn(filtered.tobytes()).set_frame_rate(8000)
    filtered_audio = filtered_audio.set_frame_rate(16000)
    return save_audio(filtered_audio, output_file)


def add_dropouts(
    input_file, output_file, count=5, min_ms=100, max_ms=300, seed=42
):
    """Insert short random silent gaps to mimic packet loss/dropouts."""
    audio = load_audio(input_file)
    samples = np.asarray(audio.get_array_of_samples(), dtype=np.int16).copy()
    rng = np.random.default_rng(seed)

    if len(samples) == 0:
        raise ValueError(f"Audio is empty: {input_file}")

    for _ in range(count):
        length = int(
            rng.integers(min_ms, max_ms + 1) * audio.frame_rate / 1000
        )
        if len(samples) <= length:
            break
        start = int(rng.integers(0, len(samples) - length + 1))
        samples[start:start + length] = 0

    return save_audio(audio._spawn(samples.tobytes()), output_file)


def add_muffled_speech(input_file, output_file, volume_db=-4, cutoff_hz=2000):
    """Approximate distant/partially obstructed speech with reduced highs and level."""
    audio = load_audio(input_file).apply_gain(volume_db)
    samples = _samples(audio)

    sos = butter(
        3, cutoff_hz, btype="lowpass", fs=audio.frame_rate, output="sos"
    )
    filtered = sosfilt(sos, samples)
    filtered = np.clip(filtered, -32768, 32767).astype(np.int16)
    muffled = audio._spawn(filtered.tobytes())
    return save_audio(muffled, output_file)


def add_mumble_proxy(input_file, output_file, speed=1.2, volume_db=-5):
    """Legacy approximation only; this does not create genuine human mumbling."""
    audio = load_audio(input_file).apply_gain(volume_db)
    samples = _samples(audio)
    sos = butter(3, 2800, btype="lowpass", fs=audio.frame_rate, output="sos")
    filtered = sosfilt(sos, samples)
    filtered = np.clip(filtered, -32768, 32767).astype(np.int16)
    softened = audio._spawn(filtered.tobytes())
    faster = softened._spawn(
        softened.raw_data,
        overrides={"frame_rate": int(softened.frame_rate * speed)},
    ).set_frame_rate(softened.frame_rate)
    return save_audio(faster, output_file)


def add_cutoff(input_file, output_file, keep_fraction=0.65):
    """Legacy helper: cut the caller off before the utterance finishes."""
    audio = load_audio(input_file)
    keep_ms = max(100, int(len(audio) * keep_fraction))
    return save_audio(audio[:keep_ms], output_file)


def create_interruption(input_file, output_file, interruption_text=None):
    """Offline fallback: simulate an interruption by cutting off the caller."""
    return add_cutoff(input_file, output_file, keep_fraction=0.60)



def _create_synthetic_background(kind: str, output_file: Path, duration_seconds: int = 12):
    """Create deterministic local fallback ambience when user-provided samples are absent.

    Real recorded traffic/fan/crowd samples are preferred. These synthetic samples
    keep the project runnable out of the box and are explicitly documented as proxies.
    """
    sample_rate = 16000
    count = sample_rate * duration_seconds
    rng = np.random.default_rng({"traffic": 101, "fan": 202, "crowd": 303}.get(kind, 404))
    white = rng.normal(0, 1, count).astype(np.float32)
    if kind == "traffic":
        sos = butter(3, 500, btype="lowpass", fs=sample_rate, output="sos")
        samples = sosfilt(sos, white)
    elif kind == "fan":
        t = np.arange(count, dtype=np.float32) / sample_rate
        samples = 0.35 * np.sin(2 * np.pi * 120 * t) + 0.15 * np.sin(2 * np.pi * 240 * t) + 0.12 * white
    else:  # crowd-like broadband babble proxy
        sos = butter(3, [250, 3200], btype="bandpass", fs=sample_rate, output="sos")
        samples = sosfilt(sos, white)
        envelope = 0.65 + 0.25 * np.sin(2 * np.pi * 2.3 * np.arange(count) / sample_rate)
        samples = samples * envelope
    peak = float(np.max(np.abs(samples))) if len(samples) else 1.0
    pcm = np.clip(samples / max(peak, 1e-8) * 12000, -32768, 32767).astype(np.int16)
    audio = AudioSegment(data=pcm.tobytes(), sample_width=2, frame_rate=sample_rate, channels=1)
    return save_audio(audio, output_file)

def generate_attack_set(
    input_dir,
    output_dir,
    noise_dir="data/background_noise",
    max_files=5,
):
    """
    Generate six attack types for the first `max_files` clean recordings.

    Required background samples:
      data/background_noise/traffic.wav
      data/background_noise/fan.wav
      data/background_noise/crowd.wav

    The caller should pass the folder where the five speech recordings live,
    not the folder containing both speech and reasoning recordings.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    noise_dir = Path(noise_dir)

    files = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    )

    if not files:
        raise FileNotFoundError(f"No audio recordings found in {input_dir}")

    if max_files is not None:
        files = files[:max_files]

    # Prefer user-provided recordings. Generate deterministic synthetic proxies
    # only for missing ambience files so a fresh clone can run without extra assets.
    for kind in BACKGROUND_TYPES:
        noise_path = noise_dir / f"{kind}.wav"
        if not noise_path.is_file():
            print(f"Background sample missing for {kind}; generating synthetic proxy.")
            _create_synthetic_background(kind, noise_path)

    print(f"Generating attacks for {len(files)} clean recordings.")
    print("Attack types: traffic, fan, crowd, phone, dropouts, muffled")

    generated = []
    for index, source in enumerate(files, start=1):
        stem = source.stem
        target_dir = output_dir / stem

        for kind, settings in BACKGROUND_TYPES.items():
            result = add_environment_noise(
                source,
                noise_dir / f"{kind}.wav",
                target_dir / f"{stem}_{kind}.wav",
                snr_db=settings["snr_db"],
                seed=42 + index,
            )
            generated.append(result)

        generated.append(
            add_phone_line(source, target_dir / f"{stem}_phone.wav")
        )
        generated.append(
            add_dropouts(
                source,
                target_dir / f"{stem}_dropouts.wav",
                seed=100 + index,
            )
        )
        generated.append(
            add_muffled_speech(
                source, target_dir / f"{stem}_muffled.wav"
            )
        )

    print(
        f"\nFinished: {len(files)} clean recordings processed; "
        f"{len(generated)} attacked recordings created."
    )
    return generated


if __name__ == "__main__":
    generate_attack_set(
        input_dir="data/recordings/timbre_test_food_delivery",
        output_dir="data/attacked/timbre_test_food_delivery",
        noise_dir="data/background_noise",
        max_files=5,
    )
