from __future__ import annotations

import json
from statistics import median
from typing import Any

from .config import ShctrlConfig
from .models import SuggestionResult
from .utils import now_iso


class TelemetryStore:
    def __init__(self, config: ShctrlConfig) -> None:
        self.config = config
        assert self.config.telemetry_path is not None
        self.path = self.config.telemetry_path

    def append(self, event_type: str, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "event_type": event_type,
            "timestamp": now_iso(),
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def log_generation(self, result: SuggestionResult) -> None:
        self.append(
            "generation",
            {
                "request_id": result.request_id,
                "intent": result.intent,
                "command": result.command,
                "annotated_command": result.annotated_command,
                "shell": result.context.shell,
                "cwd": result.context.cwd,
                "risk_score": result.risk.score,
                "risk_category": result.risk.category,
                "retrieval_count": len(result.retrievals),
                "retrieval_used": bool(result.retrievals),
                "source": result.source,
                "generation_latency_ms": result.generation_latency_ms,
            },
        )

    def log_execution(self, request_id: str, final_command: str, edited: bool, execution_latency_ms: int | None) -> None:
        self.append(
            "execution",
            {
                "request_id": request_id,
                "final_command": final_command,
                "edited_before_execute": edited,
                "execution_latency_ms": execution_latency_ms,
            },
        )

    def log_feedback(self, request_id: str, agree: bool, note: str) -> None:
        self.append(
            "feedback",
            {
                "request_id": request_id,
                "agree": agree,
                "note": note,
            },
        )

    def log_workflow_interruption(self, request_id: str, destination: str) -> None:
        self.append(
            "workflow_interruption",
            {
                "request_id": request_id,
                "destination": destination,
            },
        )

    def log_context_switch(self, request_id: str, destination: str) -> None:
        self.log_workflow_interruption(request_id=request_id, destination=destination)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows

    def metrics(self) -> dict[str, Any]:
        rows = self.load()
        generations = [row for row in rows if row["event_type"] == "generation"]
        executions = [row for row in rows if row["event_type"] == "execution"]
        feedback = [row for row in rows if row["event_type"] == "feedback"]
        interruptions = [
            row
            for row in rows
            if row["event_type"] in {"workflow_interruption", "context_switch"}
        ]

        execution_latencies = [
            row["payload"]["execution_latency_ms"]
            for row in executions
            if row["payload"].get("execution_latency_ms") is not None
        ]
        generation_latencies = [row["payload"]["generation_latency_ms"] for row in generations]
        edited_count = sum(1 for row in executions if row["payload"].get("edited_before_execute"))
        no_edit_execution_count = sum(1 for row in executions if not row["payload"].get("edited_before_execute"))
        retrieval_usage_count = sum(1 for row in generations if row["payload"].get("retrieval_used"))
        feedback_agree = sum(1 for row in feedback if row["payload"].get("agree"))
        high_risk = sum(1 for row in generations if row["payload"].get("risk_score", 0) >= 70)

        return {
            "total_suggestions": len(generations),
            "total_executions": len(executions),
            "no_edit_execution_rate": _ratio(no_edit_execution_count, len(executions)),
            "edit_before_execute_rate": _ratio(edited_count, len(executions)),
            "retrieval_usage_rate": _ratio(retrieval_usage_count, len(generations)),
            "risk_feedback_agreement_rate": _ratio(feedback_agree, len(feedback)),
            "workflow_interruption_count": len(interruptions),
            "median_generation_latency_ms": _median(generation_latencies),
            "median_time_to_execution_ms": _median(execution_latencies),
            "high_risk_suggestions": high_risk,
        }


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _median(values: list[int]) -> float | None:
    if not values:
        return None
    return round(float(median(values)), 2)
