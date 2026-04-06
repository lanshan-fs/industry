#!/bin/zsh

set -e

ROOT_DIR="/Users/bluem/Projects/Web/industrial_chain"
CONDA_BASE="/Users/bluem/miniconda3"

cleanup() {
  kill 0
}

trap cleanup INT TERM EXIT

source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate ic

(cd "$ROOT_DIR/backend_django" && python3 manage.py runserver 127.0.0.1:8000) &
(cd "$ROOT_DIR/project" && node server.js) &
(cd "$ROOT_DIR/project" && npm run dev) &

wait
