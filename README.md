# shctrl

`shctrl` is a terminal-native local language model assistant for shell command generation with retrieval grounding and inline risk annotation.

It turns natural language into shell-ready commands, looks up relevant internal runbooks/playbooks when available, scores command risk deterministically, and writes an annotated command into the active shell buffer so the user stays in control.

## Core Features

- Natural language to shell command generation
- Context grounding with shell type, OS, working directory, project markers, and selected environment signals
- Hybrid retrieval over Markdown, text, YAML, JSON, runbook, and playbook files
- Deterministic risk score from `0-100`
- Inline annotation format:

```text
find /tmp -name '*.log' -type f -mtime +7 -delete # Risk 78/100: high-risk command; confirm scope, privileges, and rollback plan; destructive file, process, or system action; broad target scope through recursion, wildcards, or system paths
```

- Shell buffer insertion:
  - PowerShell via `PSReadLine`
  - Bash via `READLINE_LINE`
  - Zsh via `zle` widget hooks
- Local telemetry and evaluation reporting
- Graceful fallback to retrieved commands if Ollama is temporarily unavailable and the runbook already contains a command template

## Repository Layout

```text
src/shctrl/
  cli.py            CLI entrypoint
  context.py        shell, OS, cwd, and project marker grounding
  retriever.py      hybrid indexing and retrieval
  prompts.py        structured prompt assembly
  ollama_client.py  local model inference
  risk.py           deterministic risk scoring and explanations
  telemetry.py      local event logging and metrics
  orchestrator.py   end-to-end suggestion pipeline

integrations/
  powershell/Shctrl.psm1
  bash/shctrl.bash
  zsh/shctrl.zsh

examples/knowledge/
  sample runbooks and playbooks

tests/
  unit tests for retrieval, prompting, orchestration, and risk scoring
```

## Quick Start

### 1. Install prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/)
- A local model such as `llama3.1:8b`

### 2. Install the project

```bash
pip install -e .
```

### 3. Pull a model in Ollama

```bash
ollama pull llama3.1:8b
```

### 4. Index your internal knowledge

```bash
shctrl index examples/knowledge
```

### 5. Generate a command

```bash
shctrl suggest "restart the log service and verify health" --shell powershell
```

## CLI Commands

```text
shctrl suggest "find large log files" --shell bash
shctrl suggest "restart the event collector" --shell powershell --json
shctrl search "restart the log service"
shctrl risk "rm -rf build/"
shctrl doctor
shctrl metrics
shctrl feedback --request-id abc123 --agree yes --note "Risk score matched expectations"
```

## Configuration

`shctrl` reads configuration from `~/.shctrl/config.json` or `SHCTRL_CONFIG`.

Example:

```json
{
  "model": "llama3.1:8b",
  "ollama_url": "http://127.0.0.1:11434",
  "knowledge_paths": [
    "C:/internal/runbooks",
    "C:/internal/playbooks"
  ],
  "retrieval_threshold": 0.2,
  "max_retrievals": 4
}
```

Environment variables:

- `SHCTRL_HOME`
- `SHCTRL_CONFIG`
- `SHCTRL_MODEL`
- `SHCTRL_OLLAMA_URL`
- `SHCTRL_KNOWLEDGE_PATHS`
- `SHCTRL_TIMEOUT_SECONDS`
- `SHCTRL_RETRIEVAL_THRESHOLD`
- `SHCTRL_MAX_RETRIEVALS`
