# VoiceCrashLab cleanup and verification

## Removed from the project bundle

- Python `__pycache__` folders and `.pyc` bytecode (generated files; recreated automatically).
- Three root-level mock scripts (`test_api_agent_mock.py`, `test_batch_runner_mock.py`, `test_adapter_runner.py`) that executed assertions and wrote files during import instead of using pytest test functions. The maintained tests live under `tests/`.

## Retained intentionally

The older CLI/STT utilities and their supporting modules remain for backwards compatibility; the dashboard's primary workflow no longer invokes the old transcript-first audio benchmark. They are not required for the new dashboard workflow, but have not been deleted because they may be useful for separate CLI experiments.

## Verification performed in this build environment

- Python `compileall`: passed.
- Manifest smoke test using temporary files: passed; 10 clean inputs + 30 attacked inputs = 40 total for five speech and five reasoning scenarios.
- API adapter mocked text-response test: passed.
- Full pytest suite was not run successfully here because required third-party packages (including Streamlit, LangChain Groq, and Groq) are not installed and package download access is unavailable in this environment. Install `requirements.txt` in your local virtual environment before running `pytest -q`.
- A real endpoint connection and live LLM/STT evaluation were not run because the ZIP does not include your `.env`, API keys, background audio recordings, or a reachable target agent. The dashboard reports per-test failures instead of silently treating them as passes.
