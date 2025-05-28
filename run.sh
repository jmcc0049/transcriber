#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/transcriber}"
source "$APP_DIR/venv/bin/activate" || { echo "Entorno virtual no encontrado; ejecutando install.sh…"; bash "$(dirname "$0")/install.sh"; source "$APP_DIR/venv/bin/activate"; }

export FLASK_ENV=production
exec gunicorn -k gevent -w "$(nproc)" -b 0.0.0.0:8000 app:app