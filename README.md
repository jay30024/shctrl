# shctrl

`shctrl` is a terminal-native local language model assistant for shell command generation with retrieval grounding and inline risk annotation.

It turns natural language into shell-ready commands, looks up relevant internal runbooks/playbooks when available, scores command risk deterministically, and writes an annotated command into the active shell buffer so the user stays in control.

## Why This Project Stands Out

- Terminal-native workflow instead of a separate chat window
- Local-first architecture using Ollama for privacy-conscious inference
- Hybrid retrieval across internal command playbooks and platform runbooks
- Deterministic risk scoring with short inline explanations
- PowerShell, Bash, and Zsh integrations
- Local telemetry for usage insights such as edit rate, retrieval usage, latency, and high-risk suggestion volume

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
- Local telemetry and usage reporting
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

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/jay30024/shctrl.git
cd shctrl
```

### 2. Create a Python environment

Windows PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

If PowerShell blocks the activation script, run this once and retry:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. Install the project

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

This exposes the `shctrl` command from the active Python environment. If you enable shell integration, that same environment must be available in the interactive shell session where you plan to press `Ctrl+g`.

### 4. Install Ollama and pull a model

- Python 3.10+
- [Ollama](https://ollama.com/)
- A local model such as `llama3.1:8b`

After Ollama is installed and running:

```bash
ollama pull llama3.1:8b
```

### 5. Verify the local install

```bash
shctrl doctor
```

`doctor` checks the local data directory, index path, telemetry path, configured knowledge roots, and whether Ollama is reachable.

## First Run

### 1. Point `shctrl` at your knowledge sources

`shctrl` discovers these folders automatically from the current working directory when they exist:

- `knowledge/`
- `runbooks/`
- `playbooks/`
- `docs/runbooks/`
- `docs/playbooks/`
- `examples/knowledge/`

You can also pass one or more explicit knowledge paths at runtime:

```bash
shctrl suggest "restart the log service" --shell powershell --knowledge-path C:/internal/runbooks
```

### 2. Optionally build the retrieval index up front

```bash
shctrl index examples/knowledge
```

This is optional. `shctrl suggest` and `shctrl search` will build the index automatically if it does not exist yet.

### 3. Generate a command

```bash
shctrl suggest "restart the log service and verify health" --shell powershell
```

### 4. Search the knowledge base directly

```bash
shctrl search "restart the log service"
```

### 5. Inspect health again if needed

```bash
shctrl doctor
```

## Shell Integration

The shell integration scripts call the `shctrl` executable directly. Before enabling them, make sure `shctrl` is already on `PATH` in the shell you are configuring.

### PowerShell

Add this to your PowerShell profile:

```powershell
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force | Out-Null }
Import-Module "C:\path\to\shctrl\integrations\powershell\Shctrl.psm1"
Register-Shctrl
```

Reload your profile:

```powershell
. $PROFILE
```

Press `Ctrl+g` to ask `shctrl` to replace the current line with an annotated suggestion. The module also hooks `Enter` so execution telemetry is logged automatically.

### Bash

Add this to `~/.bashrc`:

```bash
source /path/to/repo/integrations/bash/shctrl.bash
shctrl_enable
```

Reload your shell:

```bash
source ~/.bashrc
```

Press `Ctrl+g` to populate the current line. The script logs execution telemetry through a `DEBUG` trap.

### Zsh

Add this to `~/.zshrc`:

```zsh
source /path/to/repo/integrations/zsh/shctrl.zsh
shctrl_enable
```

Reload your shell:

```zsh
source ~/.zshrc
```

Press `Ctrl+g` to populate the current line. The script logs execution telemetry through a `preexec` hook.

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

## Usage Metrics

`shctrl metrics` summarizes local telemetry such as:

- total suggestions
- total executions
- no-edit execution rate
- edit-before-execute rate
- retrieval usage rate
- risk feedback agreement rate
- workflow interruption count
- median generation latency
- median time to execution
- high-risk suggestions

## Suggested Demo Flow

1. Index the sample knowledge base.
2. Show `shctrl suggest "restart the log service and verify health" --shell powershell --json`.
3. Show the annotated command written into the shell buffer with `Ctrl+g`.
4. Run `shctrl metrics` after a few suggestions to show local usage reporting.
