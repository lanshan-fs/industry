#!/bin/zsh

set -e

PORTS=(8000 3001 5173)

for port in "${PORTS[@]}"; do
  pids=($(lsof -ti "tcp:$port"))
  if (( ${#pids[@]} > 0 )); then
    kill "${pids[@]}"
  fi
done
