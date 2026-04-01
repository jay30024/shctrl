import tempfile
import unittest
from pathlib import Path

from shctrl.config import ShctrlConfig
from shctrl.orchestrator import ShctrlService
from shctrl.retriever import HybridRetriever
from shctrl.telemetry import TelemetryStore


class FakeOllamaClient:
    def generate(self, prompt: str) -> str:
        return "Restart-Service -Name Wecsvc"


class OrchestratorTests(unittest.TestCase):
    def test_suggest_returns_annotated_command_and_logs_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            (knowledge / "windows.md").write_text(
                "# Windows\n\nApproved procedure.\n\nRestart-Service -Name Wecsvc",
                encoding="utf-8",
            )

            config = ShctrlConfig(data_dir=root / ".shctrl", knowledge_paths=[knowledge])
            config.ensure_directories()
            retriever = HybridRetriever(config)
            retriever.build_index([knowledge])
            telemetry = TelemetryStore(config)

            service = ShctrlService(
                config=config,
                retriever=retriever,
                ollama_client=FakeOllamaClient(),
                telemetry=telemetry,
            )
            result = service.suggest(
                intent="restart the log service",
                shell="powershell",
                cwd=str(root),
            )

            self.assertEqual(result.command, "Restart-Service -Name Wecsvc")
            self.assertIn("Risk", result.annotated_command)
            self.assertTrue(telemetry.path.exists())


if __name__ == "__main__":
    unittest.main()
