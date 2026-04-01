import tempfile
import unittest
from pathlib import Path

from shctrl.config import ShctrlConfig
from shctrl.retriever import HybridRetriever


class RetrieverTests(unittest.TestCase):
    def test_index_and_search_returns_runbook_snippet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            (knowledge / "runbook.md").write_text(
                "# Restart Service\n\nApproved procedure.\n\n```bash\nsystemctl restart log-collector\n```",
                encoding="utf-8",
            )

            config = ShctrlConfig(data_dir=root / ".shctrl", knowledge_paths=[knowledge])
            config.ensure_directories()
            retriever = HybridRetriever(config)
            retriever.build_index([knowledge])
            results = retriever.search("restart the log service", [knowledge], top_k=2)

            self.assertTrue(results)
            self.assertIn("log-collector", results[0].text)


if __name__ == "__main__":
    unittest.main()
