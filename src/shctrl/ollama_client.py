from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import ShctrlConfig
from .utils import normalize_command_output


class OllamaClientError(RuntimeError):
    """Raised when Ollama is unavailable or returns an invalid response."""


class OllamaClient:
    def __init__(self, config: ShctrlConfig) -> None:
        self.config = config

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        request = urllib.request.Request(
            url=f"{self.config.ollama_url.rstrip('/')}/api/generate",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise OllamaClientError(f"Ollama request failed: {exc}") from exc

        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise OllamaClientError(f"Ollama returned non-JSON response: {response_body[:200]}") from exc

        command = normalize_command_output(str(parsed.get("response", "")))
        if not command:
            raise OllamaClientError("Ollama returned an empty command.")
        return command

    def healthcheck(self) -> tuple[bool, str]:
        request = urllib.request.Request(
            url=f"{self.config.ollama_url.rstrip('/')}/api/tags",
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=min(self.config.timeout_seconds, 5)) as response:
                if response.status == 200:
                    return True, "reachable"
                return False, f"unexpected status {response.status}"
        except (urllib.error.URLError, TimeoutError) as exc:
            return False, str(exc)
