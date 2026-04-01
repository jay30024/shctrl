from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .utils import read_json


@dataclass(slots=True)
class ShctrlConfig:
    data_dir: Path
    knowledge_paths: list[Path] = field(default_factory=list)
    index_path: Path | None = None
    telemetry_path: Path | None = None
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.1:8b"
    timeout_seconds: int = 45
    max_retrievals: int = 4
    retrieval_threshold: float = 0.20
    hash_dimensions: int = 192
    comment_prefix: str = "#"

    def __post_init__(self) -> None:
        if self.index_path is None:
            self.index_path = self.data_dir / "index.json"
        if self.telemetry_path is None:
            self.telemetry_path = self.data_dir / "telemetry" / "events.jsonl"

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        assert self.telemetry_path is not None
        self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)

    def resolved_knowledge_paths(self, cwd: str | None = None, extra_paths: list[str] | None = None) -> list[Path]:
        roots = list(self.knowledge_paths)
        if extra_paths:
            roots.extend(Path(path).expanduser() for path in extra_paths if path)
        if cwd:
            roots.extend(self._discover_workspace_knowledge(Path(cwd)))
        deduped: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            resolved = root.expanduser()
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(resolved)
        return [root for root in deduped if root.exists()]

    @staticmethod
    def _discover_workspace_knowledge(cwd: Path) -> list[Path]:
        candidates = [
            cwd / "knowledge",
            cwd / "runbooks",
            cwd / "playbooks",
            cwd / "docs" / "runbooks",
            cwd / "docs" / "playbooks",
            cwd / "examples" / "knowledge",
        ]
        return [candidate for candidate in candidates if candidate.exists()]


def load_config() -> ShctrlConfig:
    data_dir = Path(os.environ.get("SHCTRL_HOME", str(Path.home() / ".shctrl"))).expanduser()
    config_path = Path(os.environ.get("SHCTRL_CONFIG", str(data_dir / "config.json"))).expanduser()
    payload: dict = {}
    if config_path.exists():
        payload = read_json(config_path)

    knowledge_paths = _parse_path_list(
        os.environ.get("SHCTRL_KNOWLEDGE_PATHS"),
        payload.get("knowledge_paths", []),
    )
    config = ShctrlConfig(
        data_dir=data_dir,
        knowledge_paths=knowledge_paths,
        index_path=Path(payload["index_path"]).expanduser() if payload.get("index_path") else None,
        telemetry_path=Path(payload["telemetry_path"]).expanduser() if payload.get("telemetry_path") else None,
        ollama_url=os.environ.get("SHCTRL_OLLAMA_URL", payload.get("ollama_url", "http://127.0.0.1:11434")),
        model=os.environ.get("SHCTRL_MODEL", payload.get("model", "llama3.1:8b")),
        timeout_seconds=int(os.environ.get("SHCTRL_TIMEOUT_SECONDS", payload.get("timeout_seconds", 45))),
        max_retrievals=int(os.environ.get("SHCTRL_MAX_RETRIEVALS", payload.get("max_retrievals", 4))),
        retrieval_threshold=float(
            os.environ.get("SHCTRL_RETRIEVAL_THRESHOLD", payload.get("retrieval_threshold", 0.20))
        ),
        hash_dimensions=int(os.environ.get("SHCTRL_HASH_DIMENSIONS", payload.get("hash_dimensions", 192))),
        comment_prefix=str(payload.get("comment_prefix", "#")),
    )
    config.ensure_directories()
    return config


def _parse_path_list(raw_env: str | None, raw_payload: list[str]) -> list[Path]:
    paths: list[Path] = []
    if raw_env:
        paths.extend(Path(part).expanduser() for part in raw_env.split(os.pathsep) if part.strip())
    for item in raw_payload:
        if not item:
            continue
        paths.append(Path(item).expanduser())
    return paths
