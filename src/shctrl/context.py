from __future__ import annotations

import getpass
import os
import platform
from pathlib import Path

from .models import ContextSnapshot
from .utils import dedupe_preserve


MARKER_FILES = {
    ".git": "git",
    "Dockerfile": "docker",
    "docker-compose.yml": "docker-compose",
    "compose.yml": "docker-compose",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "package.json": "node",
    "pnpm-lock.yaml": "pnpm",
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "Makefile": "make",
    ".terraform": "terraform",
    "*.tf": "terraform",
    "ansible.cfg": "ansible",
    "Chart.yaml": "helm",
    "kustomization.yaml": "kubernetes",
}


def collect_context(shell: str, cwd: str | None = None, existing_buffer: str = "") -> ContextSnapshot:
    working_dir = Path(cwd or os.getcwd()).resolve()
    markers = detect_project_markers(working_dir)
    env_signals = {
        "python_venv": os.environ.get("VIRTUAL_ENV", ""),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "git_branch": os.environ.get("GIT_BRANCH", ""),
        "kube_context": os.environ.get("KUBECONTEXT", ""),
    }
    return ContextSnapshot(
        shell=shell,
        os_family=platform.system().lower(),
        cwd=str(working_dir),
        home=str(Path.home()),
        user=getpass.getuser(),
        markers=markers,
        env_signals={key: value for key, value in env_signals.items() if value},
        existing_buffer=existing_buffer,
    )


def detect_project_markers(start: Path) -> list[str]:
    candidates = [start, *list(start.parents[:2])]
    markers: list[str] = []
    for candidate in candidates:
        if not candidate.exists():
            continue
        for entry, label in MARKER_FILES.items():
            if "*" in entry:
                if list(candidate.glob(entry)):
                    markers.append(label)
                continue
            if (candidate / entry).exists():
                markers.append(label)
    return dedupe_preserve(markers)
