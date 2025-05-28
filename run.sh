#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/transcriber}"
APP_FILE="app"

# Activar entorno virtual, o instalar si no existe
if [[ ! -f "$APP_DIR/venv/bin/activate" ]]; then
    echo "Entorno virtual no encontrado. Ejecutando install.sh…"
    bash "$(dirname "$0")/install.sh"
fi

source "$APP_DIR/venv/bin/activate"

export WAITRESS_LISTEN="0.0.0.0:5000"

# Ejecutar con el servidor Waitress
cd "$APP_DIR"
waitress-serve --listen=$WAITRESS_LISTEN "$APP_FILE":app