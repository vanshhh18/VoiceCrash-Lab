"""Configuration for a generic HTTP audio-agent adapter."""
from dataclasses import dataclass
import os
from urllib.parse import urlparse


@dataclass(frozen=True)
class AgentConfig:
    name: str
    endpoint: str
    token: str = ""
    input_field: str = "audio"
    timeout: int = 120
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    response_text_field: str = "response"
    response_audio_url_field: str = "audio_url"


def validate_endpoint(endpoint: str) -> str:
    endpoint = (endpoint or "").strip()
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Endpoint must be a valid http:// or https:// URL.")
    if "example.com" in parsed.netloc.lower():
        raise ValueError("Replace the example endpoint with your real agent URL.")
    return endpoint


def load_agent_config() -> AgentConfig:
    endpoint = validate_endpoint(os.getenv("VOICE_AGENT_ENDPOINT", ""))
    timeout = int(os.getenv("VOICE_AGENT_TIMEOUT", "120"))
    if timeout < 1:
        raise ValueError("VOICE_AGENT_TIMEOUT must be positive.")
    return AgentConfig(
        name=os.getenv("VOICE_AGENT_NAME", "Connected Voice Agent"),
        endpoint=endpoint,
        token=os.getenv("VOICE_AGENT_TOKEN", ""),
        input_field=os.getenv("VOICE_AGENT_INPUT_FIELD", "audio"),
        timeout=timeout,
        auth_header=os.getenv("VOICE_AGENT_AUTH_HEADER", "Authorization"),
        auth_scheme=os.getenv("VOICE_AGENT_AUTH_SCHEME", "Bearer"),
        response_text_field=os.getenv("VOICE_AGENT_RESPONSE_TEXT_FIELD", "response"),
        response_audio_url_field=os.getenv("VOICE_AGENT_RESPONSE_AUDIO_URL_FIELD", "audio_url"),
    )
