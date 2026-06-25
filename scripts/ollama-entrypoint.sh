#!/bin/bash
set -euo pipefail

MODELS="${MODELS_TO_PULL:-nomic-embed-text,llama3.2:3b}"

/bin/ollama serve &
pid=$!

until ollama list >/dev/null 2>&1; do
  sleep 1
done

IFS=',' read -ra model_list <<< "$MODELS"
for model in "${model_list[@]}"; do
  model="$(echo "$model" | xargs)"
  [ -z "$model" ] && continue

  if ollama list | grep -qF "$model"; then
    echo "Model $model already present."
  else
    echo "Pulling $model..."
    ollama pull "$model"
  fi
done

wait "$pid"
