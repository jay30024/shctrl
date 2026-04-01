# shctrl Architecture

## Goal

`shctrl` implements the paper's core idea: a shell-native assistant that stays inside the terminal, uses local inference, reuses internal operational knowledge, and surfaces command risk exactly where execution decisions happen.

## Main Modules

### 1. Context Collector

Implemented in `src/shctrl/context.py`.

It captures:

- shell type
- OS family
- current working directory
- home directory
- current user
- project markers such as Git, Docker, Python, Node, Terraform, Kubernetes, Gradle, Maven, and Rust
- a small set of non-sensitive environment signals
- the existing shell buffer when available

### 2. Hybrid Retriever

Implemented in `src/shctrl/retriever.py`.

The retriever:

- walks configured runbook and playbook roots
- chunks documents by heading and paragraph boundaries
- builds lexical statistics for BM25-style scoring
- builds lightweight hashed semantic vectors without external ML dependencies
- combines lexical, semantic, and source/warning bonuses into a hybrid score
- supports graceful fallback by extracting command lines directly from retrieved snippets if needed

### 3. Prompt Builder

Implemented in `src/shctrl/prompts.py`.

Prompt assembly includes:

- user intent
- shell type
- OS family
- working directory
- project markers
- environment signals
- current shell buffer
- top retrieved enterprise snippets with warnings and scores

The model is instructed to return a single executable command only.

### 4. Ollama Client

Implemented in `src/shctrl/ollama_client.py`.

The client talks to a local Ollama instance over HTTP:

- `POST /api/generate` for command generation
- `GET /api/tags` for health checks

This keeps inference local and preserves the paper's privacy-focused deployment model.

### 5. Risk Engine

Implemented in `src/shctrl/risk.py`.

The risk engine uses deterministic heuristics to score commands from `0-100`.

Signals include:

- destructive actions
- privileged execution
- network and remote side effects
- broad target scope
- remote content piped directly into a shell
- persistence or permission changes
- alignment reduction based on semantic overlap with the user request
- retrieval grounding reduction when approved runbooks are found

The output format is:

```text
<command> # Risk <score>/100: <short explanation>
```

### 6. Shell Buffer Integrations

Implemented in `integrations/`.

- PowerShell:
  - `PSReadLine` key binding on `Ctrl+g`
  - line replacement through the active buffer
  - telemetry logging hooked into the `Enter` key handler
- Bash:
  - `bind -x` widget updates `READLINE_LINE`
  - `DEBUG` trap captures the next executed command
- Zsh:
  - `zle` widget updates `BUFFER`
  - `preexec` hook captures the next executed command

These scripts preserve the user as the final executor.

### 7. Telemetry and Evaluation

Implemented in `src/shctrl/telemetry.py`.

Telemetry is stored locally as JSON Lines and supports the paper's evaluation framework:

- suggestion generation events
- execution events
- user annotation feedback
- context switch logging

The `shctrl metrics` command aggregates these into summary metrics.

## Design Notes

### Why a zero-dependency Python core?

This keeps setup simple for a showcase project, avoids heavyweight packaging, and makes the product easier to run on enterprise workstations that prefer curated dependencies.

### Why hashed semantic vectors instead of external embedding libraries?

The goal here is a strong local default with minimal setup. Teams can later swap the retrieval vector representation with sentence embeddings or a dedicated vector database without changing the user-facing flow.

### Why deterministic risk scoring?

The risk comment needs to be consistent, auditable, and predictable. Deterministic scoring also makes enterprise review easier because teams can tune and validate the rules.

## Extension Points

- swap in a stronger embedding model for retrieval
- add provenance display in shell comments or structured views
- add policy packs for domain-specific rules
- add approval workflows for specific risk bands
- add a TUI dashboard for metrics and retrieval debugging
