#!/bin/bash
set -euo pipefail

MODELS="${MODELS_TO_PULL:-nomic-embed-text,llama3.2:3b}"

ollama list >/dev/null 2>&1 || exit 1

IFS=',' read -ra model_list <<< "$MODELS"
for model in "${model_list[@]}"; do
  model="$(echo "$model" | xargs)"
  [ -z "$model" ] && continue
  ollama list | grep -qF "$model" || exit 1
done
