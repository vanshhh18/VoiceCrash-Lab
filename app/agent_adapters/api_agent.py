"""Generic multipart HTTP adapter for audio-in voice agents.

The adapter supports either audio bytes, JSON containing a text response, or
JSON containing a URL to response audio. Agent-specific field names and auth
settings are configuration, not hardcoded into the benchmark pipeline.
"""
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
import mimetypes

import requests

from app.agent_adapters.base import AgentAdapter
from app.agent_adapters.config import AgentConfig, load_agent_config

ROOT = Path(__file__).resolve().parents[2]
RESPONSE_DIR = ROOT / "data" / "results" / "agent_responses"


def _nested_value(data: Any, field: str):
    """Read a configurable dotted JSON path such as data.answer.text."""
    value = data
    for part in str(field or "").split("."):
        if not part:
            continue
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


class APIAgentAdapter(AgentAdapter):
    def __init__(self, endpoint: str, token: str | None = None,
                 input_field: str = "audio", timeout: int = 120,
                 auth_header: str = "Authorization", auth_scheme: str = "Bearer",
                 response_text_field: str = "response",
                 response_audio_url_field: str = "audio_url", name: str = "Voice Agent"):
        self.endpoint = endpoint
        self.token = token or ""
        self.input_field = input_field
        self.timeout = int(timeout)
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme
        self.response_text_field = response_text_field
        self.response_audio_url_field = response_audio_url_field
        self.name = name

    @classmethod
    def from_config(cls):
        config = load_agent_config()
        return cls(**config.__dict__)

    @classmethod
    def from_mapping(cls, config: dict[str, Any]):
        return cls(
            endpoint=config["endpoint"], token=config.get("token", ""),
            input_field=config.get("input_field", "audio"),
            timeout=int(config.get("timeout", 120)),
            auth_header=config.get("auth_header", "Authorization"),
            auth_scheme=config.get("auth_scheme", "Bearer"),
            response_text_field=config.get("response_text_field", "response"),
            response_audio_url_field=config.get("response_audio_url_field", "audio_url"),
            name=config.get("name", "Voice Agent"),
        )

    def _headers(self):
        headers = {}
        if self.token:
            value = f"{self.auth_scheme} {self.token}".strip() if self.auth_scheme else self.token
            headers[self.auth_header] = value
        return headers

    def process_test(self, test_case: dict[str, Any]) -> dict[str, Any]:
        test_id = str(test_case["test_id"])
        audio_path = Path(test_case["audio_path"])
        if not audio_path.is_absolute():
            audio_path = ROOT / audio_path
        audio_path = audio_path.resolve()
        if not audio_path.is_file():
            raise FileNotFoundError(f"Input audio not found: {audio_path}")
        mime_type = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
        RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
        headers = self._headers()

        with audio_path.open("rb") as audio_file:
            response = requests.post(
                self.endpoint,
                headers=headers,
                files={self.input_field: (audio_path.name, audio_file, mime_type)},
                timeout=self.timeout,
            )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()

        result = {"test_id": test_id, "status": "success", "endpoint": self.endpoint,
                  "http_status": response.status_code, "agent_name": self.name}
        if content_type.startswith("audio/"):
            extension = mimetypes.guess_extension(content_type.split(";", 1)[0]) or ".audio"
            output_path = RESPONSE_DIR / f"{test_id}{extension}"
            output_path.write_bytes(response.content)
            result["response_audio_path"] = str(output_path)
            result["response_content_type"] = content_type
            return result

        try:
            data = response.json()
        except ValueError:
            # Some APIs return plain text instead of JSON.
            text = response.text.strip()
            if text:
                result["response_text"] = text
                return result
            raise ValueError("Agent returned an empty non-JSON response.")

        if not isinstance(data, dict):
            result["response_text"] = str(data)
            return result

        text_value = _nested_value(data, self.response_text_field)
        if not isinstance(text_value, str) or not text_value.strip():
            for key in ("response", "reply", "text", "message", "answer", "transcript"):
                candidate = data.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    text_value = candidate
                    break
        if isinstance(text_value, str) and text_value.strip():
            result["response_text"] = text_value.strip()
            result["raw_response"] = data
            return result

        audio_url = _nested_value(data, self.response_audio_url_field)
        if not isinstance(audio_url, str) or not audio_url.strip():
            for key in ("audio_url", "response_audio_url", "audio", "url"):
                candidate = data.get(key)
                if isinstance(candidate, str) and candidate.strip().startswith(("http://", "https://", "/")):
                    audio_url = candidate
                    break
        if isinstance(audio_url, str) and audio_url.strip():
            audio_url = urljoin(self.endpoint, audio_url)
            audio_response = requests.get(audio_url, headers=headers, timeout=self.timeout)
            audio_response.raise_for_status()
            response_type = audio_response.headers.get("Content-Type", "audio/mpeg").split(";", 1)[0]
            extension = mimetypes.guess_extension(response_type) or ".mp3"
            output_path = RESPONSE_DIR / f"{test_id}{extension}"
            output_path.write_bytes(audio_response.content)
            result["response_audio_path"] = str(output_path)
            result["response_content_type"] = response_type
            result["raw_response"] = data
            return result

        raise ValueError(
            "Could not find a text response or response-audio URL. Configure "
            "response_text_field or response_audio_url_field to match your API."
        )


def test_agent_connection(config: dict[str, Any]) -> dict[str, Any]:
    """Check reachability without pretending an audio request was validated."""
    from app.agent_adapters.config import validate_endpoint
    endpoint = validate_endpoint(config.get("endpoint", ""))
    token = config.get("token", "") or ""
    headers = {}
    if token:
        scheme = config.get("auth_scheme", "Bearer")
        headers[config.get("auth_header", "Authorization")] = f"{scheme} {token}".strip()
    timeout = int(config.get("timeout", 120))
    try:
        response = requests.options(endpoint, headers=headers, timeout=min(timeout, 15), allow_redirects=True)
        # OPTIONS is often disabled on API routes. Fall back to GET to distinguish
        # an unsupported method from a missing path.
        if response.status_code in (404, 405, 501):
            response = requests.get(endpoint, headers=headers, timeout=min(timeout, 15), allow_redirects=True)
        if response.status_code in (401, 403):
            raise ValueError(f"Endpoint is reachable but authentication was rejected (HTTP {response.status_code}).")
        if response.status_code in (404, 410):
            raise ValueError(f"Endpoint returned HTTP {response.status_code}; check the URL/path.")
        if response.status_code >= 500:
            raise ValueError(f"Endpoint returned server error HTTP {response.status_code} during connection check.")
        return {"status": "success", "http_status": response.status_code,
                "message": "Endpoint is reachable. Audio request schema will be validated during Test Your Agent."}
    except requests.RequestException as exc:
        raise ConnectionError(f"Could not reach agent endpoint: {exc}") from exc
