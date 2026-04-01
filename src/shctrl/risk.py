from __future__ import annotations

import re

from .models import RetrievedChunk, RiskAssessment
from .utils import tokenize


class RiskEngine:
    def __init__(self, comment_prefix: str = "#") -> None:
        self.comment_prefix = comment_prefix

    def assess(self, intent: str, command: str, shell: str, retrievals: list[RetrievedChunk]) -> RiskAssessment:
        lowered = command.lower()
        score = 8
        factors: list[tuple[int, str]] = []

        destructive_patterns = {
            "rm ": 22,
            "rm -": 22,
            "remove-item": 22,
            "del ": 20,
            "rmdir": 22,
            "rd ": 22,
            "-delete": 18,
            "kill ": 18,
            "stop-process": 18,
            "taskkill": 18,
            "shutdown": 26,
            "reboot": 26,
            "restart-computer": 26,
            "format ": 28,
            "mkfs": 28,
            "dd ": 28,
            "git clean": 20,
            "git reset --hard": 24,
            "truncate": 20,
            "drop table": 30,
        }
        for pattern, weight in destructive_patterns.items():
            if pattern in lowered:
                factors.append((weight, "destructive file, process, or system action"))
                break

        if any(token in lowered for token in ("sudo ", "doas ", "runas ", "-verb runas")):
            factors.append((18, "privileged execution or elevation requested"))

        if any(
            token in lowered
            for token in (
                "curl ",
                "wget ",
                "invoke-webrequest",
                "invoke-restmethod",
                "ssh ",
                "scp ",
                "rsync ",
                "git push",
                "docker push",
                "kubectl apply",
                "kubectl delete",
                "aws ",
                "az ",
                "gcloud ",
            )
        ):
            factors.append((14, "network or remote side effects"))

        if self._has_broad_scope(command):
            factors.append((18, "broad target scope through recursion, wildcards, or system paths"))

        if self._has_pipe_to_shell(lowered):
            factors.append((20, "remote content executed directly in a shell"))

        if any(
            token in lowered
            for token in ("chmod", "chown", "set-acl", "reg add", "set-itemproperty", "systemctl enable", "schtasks", "crontab")
        ):
            factors.append((12, "persistent environment or permission changes"))

        alignment = self._alignment_reduction(intent, command)
        if alignment > 0:
            factors.append((-alignment, "strong semantic alignment with the natural-language request"))

        retrieval_reduction = self._retrieval_reduction(retrievals)
        if retrieval_reduction > 0:
            factors.append((-retrieval_reduction, "grounded by retrieved runbook or playbook guidance"))

        score += sum(weight for weight, _ in factors)
        score = max(0, min(100, score))
        ordered = sorted(factors, key=lambda item: abs(item[0]), reverse=True)
        explanation = self._compose_explanation(score, [label for _, label in ordered], retrievals)
        category = self._category(score)
        return RiskAssessment(
            score=score,
            explanation=explanation,
            factors=[f"{weight:+d} {label}" for weight, label in ordered],
            category=category,
        )

    def annotate(self, command: str, assessment: RiskAssessment) -> str:
        return f"{command} {self.comment_prefix} Risk {assessment.score}/100: {assessment.explanation}"

    def _has_broad_scope(self, command: str) -> bool:
        lowered = command.lower()
        if any(token in command for token in ("*", "?", "[", "]")):
            return True
        if any(flag in lowered for flag in (" -r", " -rf", " --recursive", "-recurse", "/s")):
            return True
        if re.search(r"(^|\s)/(?:\s|$)", lowered):
            return True
        system_roots = ("/etc", "/usr", "/var", "c:\\", "c:\\windows", "%userprofile%", "$home", "~")
        return any(path in lowered for path in system_roots)

    def _has_pipe_to_shell(self, lowered: str) -> bool:
        return bool(
            re.search(r"(curl|wget).*\|\s*(sh|bash|zsh|pwsh|powershell)", lowered)
            or "invoke-expression" in lowered
            or re.search(r"\biex\b", lowered)
            or "eval " in lowered
        )

    def _alignment_reduction(self, intent: str, command: str) -> int:
        intent_terms = set(tokenize(intent))
        command_terms = set(tokenize(command))
        if not intent_terms or not command_terms:
            return 0
        overlap = len(intent_terms & command_terms) / max(len(intent_terms), 1)
        if overlap >= 0.55:
            return 12
        if overlap >= 0.35:
            return 7
        if overlap >= 0.20:
            return 4
        return 0

    def _retrieval_reduction(self, retrievals: list[RetrievedChunk]) -> int:
        if not retrievals:
            return 0
        top = retrievals[0]
        lowered = top.text.lower()
        if "approved" in lowered or "standard" in lowered:
            return 10
        if top.warnings:
            return 7
        return 4

    def _compose_explanation(self, score: int, labels: list[str], retrievals: list[RetrievedChunk]) -> str:
        if score <= 20:
            base = "read-only or low-impact local command"
        elif score <= 45:
            base = "moderate operational impact; review targets and flags"
        elif score <= 70:
            base = "meaningful operational risk; verify scope before execution"
        else:
            base = "high-risk command; confirm scope, privileges, and rollback plan"

        key_points: list[str] = []
        for label in labels:
            if label.startswith("strong semantic alignment") or label.startswith("grounded by"):
                continue
            if label in key_points:
                continue
            key_points.append(label)
            if len(key_points) == 2:
                break

        if retrievals and not key_points and score <= 45:
            key_points.append("retrieved enterprise guidance was available")

        if key_points:
            return f"{base}; " + "; ".join(key_points)
        return base

    def _category(self, score: int) -> str:
        if score <= 20:
            return "low"
        if score <= 45:
            return "guarded"
        if score <= 70:
            return "elevated"
        return "high"
