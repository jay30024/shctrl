import unittest

from shctrl.models import ContextSnapshot, RetrievedChunk
from shctrl.prompts import build_prompt


class PromptTests(unittest.TestCase):
    def test_prompt_contains_context_and_retrieval(self) -> None:
        context = ContextSnapshot(
            shell="powershell",
            os_family="windows",
            cwd="C:/repo",
            home="C:/Users/test",
            markers=["git", "python"],
            env_signals={"git_branch": "main"},
            existing_buffer="restart the log service",
        )
        retrievals = [
            RetrievedChunk(
                chunk_id="1",
                source_path="runbook.md",
                title="Restart",
                text="Restart-Service -Name Wecsvc",
                warnings=["approved procedure"],
                lexical_score=0.8,
                semantic_score=0.7,
                score=0.9,
            )
        ]
        prompt = build_prompt("restart the log service", context, retrievals)
        self.assertIn("powershell", prompt.lower())
        self.assertIn("Restart-Service -Name Wecsvc", prompt)
        self.assertIn("git_branch=main", prompt)


if __name__ == "__main__":
    unittest.main()
