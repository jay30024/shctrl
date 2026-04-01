from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from .config import ShctrlConfig
from .models import IndexChunk, KnowledgeIndex, RetrievedChunk
from .utils import (
    bm25,
    chunk_markdown,
    cosine_sparse,
    extract_command_candidates,
    hashed_vector,
    now_iso,
    read_json,
    read_text,
    token_counts,
    tokenize,
    write_json,
)

SUPPORTED_EXTENSIONS = {
    ".md",
    ".txt",
    ".rst",
    ".adoc",
    ".runbook",
    ".playbook",
    ".yaml",
    ".yml",
    ".json",
}


class HybridRetriever:
    def __init__(self, config: ShctrlConfig) -> None:
        self.config = config

    def build_index(self, roots: list[Path]) -> KnowledgeIndex:
        chunks: list[IndexChunk] = []
        doc_freq_counter: Counter[str] = Counter()
        for root in roots:
            if root.is_file():
                source_files = [root]
            else:
                source_files = [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]
            for file_path in source_files:
                text = read_text(file_path)
                warnings = extract_warnings(text)
                for index, (title, body) in enumerate(chunk_markdown(text)):
                    counts = token_counts(body)
                    if not counts:
                        continue
                    vector = hashed_vector(body, dimensions=self.config.hash_dimensions)
                    chunk = IndexChunk(
                        chunk_id=f"{file_path}:{index}",
                        source_path=str(file_path),
                        title=title,
                        text=body,
                        length=sum(counts.values()),
                        token_counts=counts,
                        vector=vector,
                        warnings=warnings,
                    )
                    chunks.append(chunk)
                    doc_freq_counter.update(set(counts))

        average_length = sum(chunk.length for chunk in chunks) / max(len(chunks), 1)
        index = KnowledgeIndex(
            version=1,
            built_at=now_iso(),
            source_roots=[str(root) for root in roots],
            avg_length=average_length or 1.0,
            doc_freq=dict(doc_freq_counter),
            chunks=chunks,
        )
        assert self.config.index_path is not None
        write_json(self.config.index_path, index.to_dict())
        return index

    def load_index(self) -> KnowledgeIndex | None:
        assert self.config.index_path is not None
        if not self.config.index_path.exists():
            return None
        return KnowledgeIndex.from_dict(read_json(self.config.index_path))

    def ensure_index(self, roots: list[Path]) -> KnowledgeIndex | None:
        if not roots:
            return self.load_index()
        index = self.load_index()
        if index is None:
            return self.build_index(roots)

        indexed_roots = {str(Path(root).expanduser()) for root in index.source_roots}
        requested_roots = {str(root.expanduser()) for root in roots}
        if not requested_roots.issubset(indexed_roots):
            return self.build_index(roots)
        return index

    def search(self, query: str, roots: list[Path], top_k: int | None = None) -> list[RetrievedChunk]:
        index = self.ensure_index(roots)
        if index is None or not index.chunks:
            return []

        limit = top_k or self.config.max_retrievals
        query_terms = tokenize(query)
        query_vector = hashed_vector(query, dimensions=self.config.hash_dimensions)
        lexical_raw: list[float] = []
        semantic_raw: list[float] = []
        for chunk in index.chunks:
            lexical_raw.append(
                bm25(
                    query_terms,
                    chunk.token_counts,
                    index.doc_freq,
                    len(index.chunks),
                    index.avg_length,
                    chunk.length,
                )
            )
            semantic_raw.append(cosine_sparse(query_vector, chunk.vector))

        lexical_max = max(lexical_raw, default=1.0) or 1.0
        results: list[RetrievedChunk] = []
        for position, chunk in enumerate(index.chunks):
            lexical = lexical_raw[position] / lexical_max
            semantic = semantic_raw[position]
            source_bonus = 0.08 if any(tag in chunk.source_path.lower() for tag in ("runbook", "playbook")) else 0.0
            warning_bonus = 0.04 if chunk.warnings else 0.0
            score = min(1.0, (0.60 * lexical) + (0.32 * semantic) + source_bonus + warning_bonus)
            if score <= 0:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    source_path=chunk.source_path,
                    title=chunk.title,
                    text=chunk.text,
                    warnings=chunk.warnings,
                    lexical_score=round(lexical, 4),
                    semantic_score=round(semantic, 4),
                    score=round(score, 4),
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        if not results:
            return []

        filtered = [item for item in results if item.score >= self.config.retrieval_threshold]
        chosen = filtered[:limit] if filtered else results[:limit]
        return chosen

    def extract_fallback_command(self, retrievals: list[RetrievedChunk]) -> str:
        best_score = -math.inf
        best_candidate = ""
        for chunk in retrievals:
            for candidate in extract_command_candidates(chunk.text):
                score = chunk.score + len(candidate) / 1000.0
                if score > best_score:
                    best_score = score
                    best_candidate = candidate
        return best_candidate


def extract_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    lowered = text.lower()
    mapping = {
        "approved": "approved procedure",
        "dry run": "dry-run available",
        "backup": "backup recommended",
        "maintenance window": "maintenance window required",
        "sudo": "requires elevation",
        "administrator": "requires elevation",
        "rollback": "rollback guidance present",
        "verify": "verification steps present",
    }
    for phrase, label in mapping.items():
        if phrase in lowered:
            warnings.append(label)
    return warnings
