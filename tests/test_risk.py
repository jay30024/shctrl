import unittest

from shctrl.risk import RiskEngine


class RiskEngineTests(unittest.TestCase):
    def test_recursive_delete_scores_high(self) -> None:
        engine = RiskEngine()
        assessment = engine.assess(
            intent="delete old log files",
            command="find /tmp -name '*.log' -type f -mtime +7 -delete",
            shell="bash",
            retrievals=[],
        )
        self.assertGreaterEqual(assessment.score, 60)
        self.assertIn("risk", f"Risk {assessment.score}/100: {assessment.explanation}".lower())

    def test_read_only_command_scores_low(self) -> None:
        engine = RiskEngine()
        assessment = engine.assess(
            intent="show docker containers",
            command="docker ps",
            shell="bash",
            retrievals=[],
        )
        self.assertLessEqual(assessment.score, 25)


if __name__ == "__main__":
    unittest.main()
