from __future__ import annotations

from .models import ContextSnapshot, RetrievedChunk


def build_prompt(intent: str, context: ContextSnapshot, retrievals: list[RetrievedChunk]) -> str:
    retrieval_block = _render_retrievals(retrievals)
    markers = ", ".join(context.markers) if context.markers else "none"
    env_signals = ", ".join(f"{key}={value}" for key, value in context.env_signals.items()) or "none"
    buffer = context.existing_buffer or "empty"
    return f"""You are shctrl, a terminal-native command generation assistant.

Return exactly one executable {context.shell} command for the user's intent.
Rules:
- Output command text only.
- Do not use Markdown.
- Do not wrap the command in quotes or backticks.
- Do not explain the command.
- Prefer the current shell's native syntax and quoting.
- Use commands that fit the operating system family.
- If the task is destructive, prefer a safer preview/check variant when possible without ignoring the user's request.
- If retrieval snippets define exact service names, paths, or verification steps, honor them.

Intent:
{intent}

Active shell context:
- shell: {context.shell}
- os_family: {context.os_family}
- cwd: {context.cwd}
- project_markers: {markers}
- environment_signals: {env_signals}
- existing_buffer: {buffer}

Retrieved enterprise knowledge:
{retrieval_block}

Generate the single best command now."""


def _render_retrievals(retrievals: list[RetrievedChunk]) -> str:
    if not retrievals:
        return "- none"
    blocks: list[str] = []
    for index, chunk in enumerate(retrievals, start=1):
        warning_text = ", ".join(chunk.warnings) if chunk.warnings else "none"
        blocks.append(
            f"""- snippet {index}
  source: {chunk.source_path}
  title: {chunk.title}
  warnings: {warning_text}
  score: {chunk.score}
  body:
{indent(chunk.text, '    ')}"""
        )
    return "\n".join(blocks)


def indent(text: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" if line else prefix.rstrip() for line in text.splitlines())
