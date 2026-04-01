from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

TOKEN_RE = re.compile(r"[A-Za-z0-9_./:%@-]+")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def semantic_terms(text: str) -> list[str]:
    tokens = tokenize(text)
    expanded = list(tokens)
    for token in tokens:
        if len(token) < 5:
            continue
        expanded.extend(token[index : index + 3] for index in range(len(token) - 2))
    return expanded


def token_counts(text: str) -> dict[str, int]:
    return dict(Counter(tokenize(text)))


def hashed_vector(text: str, dimensions: int = 192) -> dict[str, float]:
    counts = Counter(semantic_terms(text))
    vector: dict[str, float] = {}
    for token, count in counts.items():
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % dimensions
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        key = str(bucket)
        vector[key] = vector.get(key, 0.0) + (count * sign)

    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {key: value / norm for key, value in vector.items()}


def cosine_sparse(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    dot = 0.0
    for key, value in left.items():
        dot += value * right.get(key, 0.0)
    return max(0.0, min(1.0, dot))


def bm25(
    query_tokens: list[str],
    counts: dict[str, int],
    doc_freq: dict[str, int],
    total_docs: int,
    avg_doc_length: float,
    doc_length: int,
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    score = 0.0
    doc_length = max(doc_length, 1)
    avg_doc_length = max(avg_doc_length, 1.0)
    for token in query_tokens:
        frequency = counts.get(token, 0)
        if frequency <= 0:
            continue
        df = max(doc_freq.get(token, 0), 0)
        idf = math.log(1 + ((total_docs - df + 0.5) / (df + 0.5)))
        numerator = frequency * (k1 + 1.0)
        denominator = frequency + k1 * (1.0 - b + (b * doc_length / avg_doc_length))
        score += idf * (numerator / denominator)
    return score


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def json_dumps(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def normalize_command_output(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return lines[0].strip("`")


def heading_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = "General"
    current_lines: list[str] = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
                current_lines = []
            current_title = match.group(1).strip()
            continue
        current_lines.append(line)
    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return [(title, body) for title, body in sections if body]


def chunk_markdown(text: str, max_chars: int = 900, overlap_chars: int = 150) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    for title, body in heading_sections(text):
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
        buffer = ""
        for paragraph in paragraphs:
            if not buffer:
                buffer = paragraph
                continue
            candidate = f"{buffer}\n\n{paragraph}"
            if len(candidate) <= max_chars:
                buffer = candidate
                continue
            chunks.append((title, buffer))
            overlap = buffer[-overlap_chars:] if overlap_chars and len(buffer) > overlap_chars else ""
            buffer = f"{overlap}\n{paragraph}".strip()
        if buffer:
            chunks.append((title, buffer))
    return chunks


def looks_like_command(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "//", "*", "- ")):
        return False
    command_heads = (
        "git",
        "kubectl",
        "docker",
        "find",
        "grep",
        "awk",
        "sed",
        "ls",
        "rm",
        "cp",
        "mv",
        "python",
        "pip",
        "npm",
        "yarn",
        "pnpm",
        "curl",
        "wget",
        "ssh",
        "scp",
        "systemctl",
        "journalctl",
        "Get-",
        "Set-",
        "Stop-",
        "Start-",
        "Restart-",
        "Invoke-",
        "Test-",
        ".\\",
        "./",
    )
    return stripped.startswith(command_heads)


def extract_command_candidates(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if looks_like_command(line)]


def dedupe_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
