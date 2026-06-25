#!/bin/sh
set -eu

BUCKET="${MINIO_BUCKET:-pdf-documents}"

minio server /data --console-address ":9001" &
pid=$!

until mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" 2>/dev/null \
      && mc ready local >/dev/null 2>&1; do
  sleep 1
done

mc mb "local/${BUCKET}" --ignore-existing

wait "$pid"
