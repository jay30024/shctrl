typeset -g SHCTRL_PENDING_REQUEST_ID=""
typeset -g SHCTRL_PENDING_RAW_COMMAND=""
typeset -g SHCTRL_PENDING_ANNOTATED_COMMAND=""
typeset -g SHCTRL_INSERTED_AT_MS=""

_shctrl_python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    print -r -- python3
    return
  fi
  print -r -- python
}

_shctrl_now_ms() {
  "$(_shctrl_python_bin)" -c "import time; print(int(time.time() * 1000))"
}

shctrl-widget() {
  local intent="$BUFFER"
  if [[ -z "$intent" ]]; then
    vared -p "shctrl> " intent || return
  fi

  local output
  output="$(shctrl suggest "$intent" --shell zsh --cwd "$PWD" --existing-buffer "$BUFFER" --tsv)" || return

  local request_id raw_command annotated_command
  IFS=$'\t' read -r request_id raw_command annotated_command <<< "$output"
  [[ -z "$annotated_command" ]] && return

  BUFFER="$annotated_command"
  CURSOR=${#BUFFER}
  SHCTRL_PENDING_REQUEST_ID="$request_id"
  SHCTRL_PENDING_RAW_COMMAND="$raw_command"
  SHCTRL_PENDING_ANNOTATED_COMMAND="$annotated_command"
  SHCTRL_INSERTED_AT_MS="$(_shctrl_now_ms)"
}

shctrl-preexec() {
  local command_text="$1"
  [[ -z "$SHCTRL_PENDING_REQUEST_ID" ]] && return
  [[ "$command_text" == "shctrl log-execution"* ]] && return
  [[ "$command_text" == "_shctrl_"* ]] && return

  local latency=""
  if [[ -n "$SHCTRL_INSERTED_AT_MS" ]]; then
    latency="$(( $(_shctrl_now_ms) - SHCTRL_INSERTED_AT_MS ))"
  fi

  local request_id="$SHCTRL_PENDING_REQUEST_ID"
  local raw_command="$SHCTRL_PENDING_RAW_COMMAND"
  SHCTRL_PENDING_REQUEST_ID=""
  SHCTRL_PENDING_RAW_COMMAND=""
  SHCTRL_PENDING_ANNOTATED_COMMAND=""
  SHCTRL_INSERTED_AT_MS=""

  local args
  args=(log-execution --request-id "$request_id" --final-command "$command_text")
  if [[ "$command_text" != "$raw_command" ]]; then
    args+=(--edited)
  fi
  if [[ -n "$latency" ]]; then
    args+=(--execution-latency-ms "$latency")
  fi
  shctrl "${args[@]}" >/dev/null 2>&1
}

shctrl_enable() {
  autoload -Uz add-zsh-hook
  zle -N shctrl-widget
  bindkey '^G' shctrl-widget
  add-zsh-hook preexec shctrl-preexec
}
