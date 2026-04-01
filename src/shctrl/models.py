from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ContextSnapshot:
    shell: str
    os_family: str
    cwd: str
    home: str
    user: str = ""
    markers: list[str] = field(default_factory=list)
    env_signals: dict[str, str] = field(default_factory=dict)
    existing_buffer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    source_path: str
    title: str
    text: str
    warnings: list[str]
    lexical_score: float
    semantic_score: float
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RiskAssessment:
    score: int
    explanation: str
    factors: list[str]
    category: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SuggestionResult:
    request_id: str
    intent: str
    command: str
    annotated_command: str
    prompt: str
    context: ContextSnapshot
    retrievals: list[RetrievedChunk]
    risk: RiskAssessment
    source: str
    generation_latency_ms: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["context"] = self.context.to_dict()
        payload["retrievals"] = [chunk.to_dict() for chunk in self.retrievals]
        payload["risk"] = self.risk.to_dict()
        return payload


@dataclass(slots=True)
class IndexChunk:
    chunk_id: str
    source_path: str
    title: str
    text: str
    length: int
    token_counts: dict[str, int]
    vector: dict[str, float]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KnowledgeIndex:
    version: int
    built_at: str
    source_roots: list[str]
    avg_length: float
    doc_freq: dict[str, int]
    chunks: list[IndexChunk]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "built_at": self.built_at,
            "source_roots": self.source_roots,
            "avg_length": self.avg_length,
            "doc_freq": self.doc_freq,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowledgeIndex":
        return cls(
            version=int(payload["version"]),
            built_at=str(payload["built_at"]),
            source_roots=list(payload.get("source_roots", [])),
            avg_length=float(payload.get("avg_length", 1.0)),
            doc_freq={str(key): int(value) for key, value in payload.get("doc_freq", {}).items()},
            chunks=[
                IndexChunk(
                    chunk_id=str(chunk["chunk_id"]),
                    source_path=str(chunk["source_path"]),
                    title=str(chunk.get("title", "")),
                    text=str(chunk["text"]),
                    length=int(chunk["length"]),
                    token_counts={str(k): int(v) for k, v in chunk.get("token_counts", {}).items()},
                    vector={str(k): float(v) for k, v in chunk.get("vector", {}).items()},
                    warnings=list(chunk.get("warnings", [])),
                )
                for chunk in payload.get("chunks", [])
            ],
        )
