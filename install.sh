#!/usr/bin/env bash
set -euo pipefail

# === Parameters ===
REPO_URL="https://github.com/jmcc0049/transcriber.git"
APP_DIR="${APP_DIR:-$HOME/transcriber}"

echo "==> Instalando dependencias del sistema…"
sudo apt update
sudo apt install -y \
    ffmpeg libheif1 libheif-dev libheif-examples \
    python3 python3-pip python-is-python3 python3-venv \
    build-essential git

echo "==> Cloning/updating repository in $APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" pull
else
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> Creando entorno virtual…"
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"

echo "==> Installing Python requirements…"
pip3 install --upgrade pip
pip3 install -r "$APP_DIR/requirements.txt"

echo "==> Instalación completada"