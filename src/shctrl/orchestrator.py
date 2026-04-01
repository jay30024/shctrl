from __future__ import annotations

import time

from .config import ShctrlConfig
from .context import collect_context
from .models import SuggestionResult
from .ollama_client import OllamaClient, OllamaClientError
from .prompts import build_prompt
from .retriever import HybridRetriever
from .risk import RiskEngine
from .telemetry import TelemetryStore
from .utils import new_request_id


class ShctrlService:
    def __init__(
        self,
        config: ShctrlConfig,
        retriever: HybridRetriever | None = None,
        ollama_client: OllamaClient | None = None,
        risk_engine: RiskEngine | None = None,
        telemetry: TelemetryStore | None = None,
    ) -> None:
        self.config = config
        self.retriever = retriever or HybridRetriever(config)
        self.ollama_client = ollama_client or OllamaClient(config)
        self.risk_engine = risk_engine or RiskEngine(comment_prefix=config.comment_prefix)
        self.telemetry = telemetry or TelemetryStore(config)

    def suggest(
        self,
        intent: str,
        shell: str,
        cwd: str | None = None,
        existing_buffer: str = "",
        knowledge_paths: list[str] | None = None,
    ) -> SuggestionResult:
        request_id = new_request_id()
        context = collect_context(shell=shell, cwd=cwd, existing_buffer=existing_buffer)
        resolved_knowledge_paths = self.config.resolved_knowledge_paths(context.cwd, knowledge_paths)
        retrievals = self.retriever.search(intent, resolved_knowledge_paths)
        prompt = build_prompt(intent=intent, context=context, retrievals=retrievals)

        started = time.perf_counter()
        source = "ollama"
        try:
            command = self.ollama_client.generate(prompt)
        except OllamaClientError:
            fallback = self.retriever.extract_fallback_command(retrievals)
            if not fallback:
                raise
            command = fallback
            source = "retrieval-fallback"
        latency_ms = int((time.perf_counter() - started) * 1000)

        assessment = self.risk_engine.assess(intent=intent, command=command, shell=shell, retrievals=retrievals)
        annotated = self.risk_engine.annotate(command, assessment)
        result = SuggestionResult(
            request_id=request_id,
            intent=intent,
            command=command,
            annotated_command=annotated,
            prompt=prompt,
            context=context,
            retrievals=retrievals,
            risk=assessment,
            source=source,
            generation_latency_ms=latency_ms,
        )
        self.telemetry.log_generation(result)
        return result
