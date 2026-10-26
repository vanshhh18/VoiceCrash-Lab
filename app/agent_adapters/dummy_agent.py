import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.agent_adapters.base import AgentAdapter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMMY_AGENT_DIR = Path.home() / "Desktop" / "DummyAgent"


class DummyAgentAdapter(AgentAdapter):
    """Adapter for the existing DummyAgent application."""

    def process_test(self, test_case: dict[str, Any]) -> dict[str, Any]:
        test_id = test_case["test_id"]

        audio_path = Path(test_case["audio_path"])
        if not audio_path.is_absolute():
            audio_path = PROJECT_ROOT / audio_path

        python_exe = DUMMY_AGENT_DIR / "venv" / "Scripts" / "python.exe"
        app_file = DUMMY_AGENT_DIR / "app.py"

        if not audio_path.is_file():
            raise FileNotFoundError(f"Input audio not found: {audio_path}")

        if not python_exe.is_file():
            raise FileNotFoundError(f"DummyAgent Python not found: {python_exe}")

        if not app_file.is_file():
            raise FileNotFoundError(f"DummyAgent app not found: {app_file}")

        generated_audio = (
            DUMMY_AGENT_DIR
            / "responses"
            / f"{audio_path.stem}_response.mp3"
        )

        if generated_audio.exists():
            generated_audio.unlink()

        subprocess.run(
            [str(python_exe), str(app_file), str(audio_path)],
            cwd=str(DUMMY_AGENT_DIR),
            check=True,
        )

        if not generated_audio.is_file():
            raise FileNotFoundError(
                f"DummyAgent did not generate expected audio: {generated_audio}"
            )

        output_dir = PROJECT_ROOT / "data" / "results" / "agent_responses"
        output_dir.mkdir(parents=True, exist_ok=True)

        destination = output_dir / f"{test_id}.mp3"
        shutil.copy2(generated_audio, destination)

        return {
            "test_id": test_id,
            "status": "success",
            "response_audio_path": str(destination),
        }