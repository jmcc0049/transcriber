#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/transcriber}"
APP_FILE="app.py"

# Activar entorno virtual, o instalar si no existe
if [[ ! -f "$APP_DIR/venv/bin/activate" ]]; then
    echo "Entorno virtual no encontrado. Ejecutando install.sh…"
    bash "$(dirname "$0")/install.sh"
fi

source "$APP_DIR/venv/bin/activate"

export FLASK_APP="$APP_FILE"
export FLASK_ENV=production
export FLASK_RUN_PORT=8000
export FLASK_RUN_HOST=0.0.0.0

# Ejecutar con el servidor de desarrollo de Flask
flask run