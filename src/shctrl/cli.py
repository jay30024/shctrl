from __future__ import annotations

import argparse
import os
import sys

from .config import load_config
from .ollama_client import OllamaClient
from .orchestrator import ShctrlService
from .retriever import HybridRetriever
from .risk import RiskEngine
from .telemetry import TelemetryStore
from .utils import json_dumps


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shctrl", description="Terminal-native local shell command assistant.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    suggest = subparsers.add_parser("suggest", help="Generate an annotated shell command.")
    suggest.add_argument("intent", help="Natural language intent to convert into a command.")
    suggest.add_argument("--shell", default="powershell", choices=["powershell", "bash", "zsh"], help="Target shell.")
    suggest.add_argument("--cwd", default=None, help="Working directory to ground the prompt.")
    suggest.add_argument("--existing-buffer", default="", help="Current shell buffer contents.")
    suggest.add_argument(
        "--knowledge-path",
        action="append",
        default=[],
        help="Additional knowledge directory or file. Can be provided multiple times.",
    )
    suggest.add_argument("--tsv", action="store_true", help="Emit request id, raw command, and annotated command as TSV.")
    suggest.add_argument("--json", action="store_true", help="Emit full JSON payload.")

    index = subparsers.add_parser("index", help="Index knowledge files for hybrid retrieval.")
    index.add_argument("paths", nargs="*", help="Knowledge roots to index.")
    index.add_argument("--json", action="store_true", help="Emit JSON summary.")

    search = subparsers.add_parser("search", help="Search the knowledge index without generating a command.")
    search.add_argument("query", help="Retrieval query.")
    search.add_argument("--top-k", type=int, default=4, help="Number of results to return.")
    search.add_argument(
        "--knowledge-path",
        action="append",
        default=[],
        help="Additional knowledge directory or file. Can be provided multiple times.",
    )
    search.add_argument("--cwd", default=None, help="Working directory used to discover knowledge paths.")
    search.add_argument("--json", action="store_true", help="Emit JSON payload.")

    risk = subparsers.add_parser("risk", help="Score a command with the deterministic risk engine.")
    risk.add_argument("command_text", help="Command to assess.")
    risk.add_argument("--intent", default="", help="Optional natural-language intent for alignment scoring.")
    risk.add_argument("--json", action="store_true", help="Emit JSON payload.")

    doctor = subparsers.add_parser("doctor", help="Check local installation health.")
    doctor.add_argument("--json", action="store_true", help="Emit JSON payload.")

    executed = subparsers.add_parser("log-execution", help="Record execution telemetry from shell integrations.")
    executed.add_argument("--request-id", required=True, help="Request id from a previous suggestion.")
    executed.add_argument("--final-command", required=True, help="The command the user executed.")
    executed.add_argument("--edited", action="store_true", help="Mark the command as edited before execution.")
    executed.add_argument("--execution-latency-ms", type=int, default=None, help="Elapsed time from insertion to run.")

    feedback = subparsers.add_parser("feedback", help="Record user feedback on risk annotation quality.")
    feedback.add_argument("--request-id", required=True, help="Request id from a previous suggestion.")
    feedback.add_argument("--agree", choices=["yes", "no"], required=True, help="Whether the annotation felt correct.")
    feedback.add_argument("--note", default="", help="Optional feedback note.")

    context_switch = subparsers.add_parser("log-context-switch", help="Record a context switch for evaluation studies.")
    context_switch.add_argument("--request-id", required=True, help="Request id from a previous suggestion.")
    context_switch.add_argument("--destination", required=True, help="Where the user went, e.g. browser, docs, wiki.")

    metrics = subparsers.add_parser("metrics", help="Aggregate local telemetry into evaluation metrics.")
    metrics.add_argument("--json", action="store_true", help="Emit JSON payload.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()
    retriever = HybridRetriever(config)
    telemetry = TelemetryStore(config)

    if args.command == "index":
        roots = config.resolved_knowledge_paths(cwd=os.getcwd(), extra_paths=args.paths)
        if not roots:
            parser.error("No knowledge paths found to index.")
        index = retriever.build_index(roots)
        payload = {
            "built_at": index.built_at,
            "chunk_count": len(index.chunks),
            "source_roots": index.source_roots,
            "index_path": str(config.index_path),
        }
        _emit(payload, args.json)
        return 0

    if args.command == "search":
        roots = config.resolved_knowledge_paths(cwd=args.cwd or os.getcwd(), extra_paths=args.knowledge_path)
        results = retriever.search(args.query, roots, top_k=args.top_k)
        payload = {"results": [item.to_dict() for item in results], "count": len(results)}
        _emit(payload, args.json)
        return 0

    if args.command == "suggest":
        service = ShctrlService(config=config, retriever=retriever, telemetry=telemetry)
        result = service.suggest(
            intent=args.intent,
            shell=args.shell,
            cwd=args.cwd,
            existing_buffer=args.existing_buffer,
            knowledge_paths=args.knowledge_path,
        )
        if args.json:
            print(json_dumps(result.to_dict()))
        elif args.tsv:
            print(f"{result.request_id}\t{result.command}\t{result.annotated_command}")
        else:
            print(result.annotated_command)
        return 0

    if args.command == "risk":
        assessment = RiskEngine(comment_prefix=config.comment_prefix).assess(
            intent=args.intent,
            command=args.command_text,
            shell="powershell",
            retrievals=[],
        )
        payload = assessment.to_dict()
        _emit(payload, args.json)
        return 0

    if args.command == "doctor":
        ollama = OllamaClient(config)
        healthy, detail = ollama.healthcheck()
        assert config.index_path is not None
        payload = {
            "data_dir": str(config.data_dir),
            "index_path": str(config.index_path),
            "index_exists": config.index_path.exists(),
            "ollama_url": config.ollama_url,
            "ollama_status": {"healthy": healthy, "detail": detail},
            "knowledge_paths": [str(path) for path in config.knowledge_paths],
            "telemetry_path": str(config.telemetry_path),
        }
        _emit(payload, args.json)
        return 0 if healthy else 1

    if args.command == "log-execution":
        telemetry.log_execution(
            request_id=args.request_id,
            final_command=args.final_command,
            edited=args.edited,
            execution_latency_ms=args.execution_latency_ms,
        )
        print("ok")
        return 0

    if args.command == "feedback":
        telemetry.log_feedback(
            request_id=args.request_id,
            agree=args.agree == "yes",
            note=args.note,
        )
        print("ok")
        return 0

    if args.command == "log-context-switch":
        telemetry.log_context_switch(
            request_id=args.request_id,
            destination=args.destination,
        )
        print("ok")
        return 0

    if args.command == "metrics":
        payload = telemetry.metrics()
        _emit(payload, args.json)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json_dumps(payload))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    sys.exit(main())
