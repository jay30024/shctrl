_shctrl_python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    printf '%s\n' python3
    return
  fi
  printf '%s\n' python
}

_shctrl_now_ms() {
  "$(_shctrl_python_bin)" -c "import time; print(int(time.time() * 1000))"
}

_shctrl_widget() {
  local intent="$READLINE_LINE"
  if [[ -z "$intent" ]]; then
    read -er -p "shctrl> " intent || return
  fi

  local output
  output="$(shctrl suggest "$intent" --shell bash --cwd "$PWD" --existing-buffer "$READLINE_LINE" --tsv)" || return

  local request_id raw_command annotated_command
  IFS=$'\t' read -r request_id raw_command annotated_command <<< "$output"
  if [[ -z "$annotated_command" ]]; then
    return
  fi

  READLINE_LINE="$annotated_command"
  READLINE_POINT=${#READLINE_LINE}
  SHCTRL_PENDING_REQUEST_ID="$request_id"
  SHCTRL_PENDING_RAW_COMMAND="$raw_command"
  SHCTRL_PENDING_ANNOTATED_COMMAND="$annotated_command"
  SHCTRL_INSERTED_AT_MS="$(_shctrl_now_ms)"
}

_shctrl_preexec() {
  local command_text="$1"
  [[ -z "${SHCTRL_PENDING_REQUEST_ID:-}" ]] && return
  [[ "$command_text" == "shctrl log-execution"* ]] && return
  [[ "$command_text" == "_shctrl_"* ]] && return

  local latency=""
  if [[ -n "${SHCTRL_INSERTED_AT_MS:-}" ]]; then
    latency="$(( $(_shctrl_now_ms) - SHCTRL_INSERTED_AT_MS ))"
  fi

  local request_id="$SHCTRL_PENDING_REQUEST_ID"
  local raw_command="$SHCTRL_PENDING_RAW_COMMAND"
  SHCTRL_PENDING_REQUEST_ID=""
  SHCTRL_PENDING_RAW_COMMAND=""
  SHCTRL_PENDING_ANNOTATED_COMMAND=""
  SHCTRL_INSERTED_AT_MS=""

  local args=(log-execution --request-id "$request_id" --final-command "$command_text")
  if [[ "$command_text" != "$raw_command" ]]; then
    args+=(--edited)
  fi
  if [[ -n "$latency" ]]; then
    args+=(--execution-latency-ms "$latency")
  fi
  shctrl "${args[@]}" >/dev/null 2>&1
}

shctrl_enable() {
  bind -x '"\C-g":_shctrl_widget'
  trap '_shctrl_preexec "$BASH_COMMAND"' DEBUG
}
