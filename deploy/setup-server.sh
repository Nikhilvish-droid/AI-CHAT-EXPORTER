#!/usr/bin/env bash
# Sets up (or updates) the backend + Nginx on an Ubuntu 24.04 EC2 instance.
# Safe to re-run: after a `git pull`, run it again to reinstall deps and restart.
#
# Usage, as the normal login user (ubuntu), from the repo root on the server:
#   bash deploy/setup-server.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="$(id -un)"
WEB_ROOT=/var/www/chat-exporter
SWAP_SIZE="${SWAP_SIZE:-4G}"

if [ "$(id -u)" -eq 0 ]; then
    echo "Run this as your normal user (e.g. ubuntu), not root - it uses sudo where needed."
    exit 1
fi

echo "==> Swap ($SWAP_SIZE)"
# torch + the embedding model + headless Chromium do not fit in 1 GB of RAM.
if ! swapon --show | grep -q '^/swapfile'; then
    [ -f /swapfile ] || sudo fallocate -l "$SWAP_SIZE" /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile >/dev/null
    sudo swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "==> System packages"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3-venv python3-pip python3-dev build-essential nginx git curl

echo "==> Python environment"
cd "$APP_DIR/backend"
[ -d venv ] || python3 -m venv venv
export PIP_NO_CACHE_DIR=1
venv/bin/pip install --upgrade pip

# CPU-only torch first. Otherwise pip pulls several GB of CUDA libraries that
# are useless on an instance without a GPU. requirements.txt then sees torch
# as already satisfied (2.x.y+cpu matches ==2.x.y).
TORCH_VERSION="$(grep -E '^torch==' requirements.txt | cut -d= -f3)"
venv/bin/pip install "torch==${TORCH_VERSION}" --index-url https://download.pytorch.org/whl/cpu
venv/bin/pip install -r requirements.txt

echo "==> Playwright Chromium (used by the Gemini scraper)"
venv/bin/playwright install chromium
sudo "$APP_DIR/backend/venv/bin/playwright" install-deps chromium

echo "==> Backend config"
if [ ! -f .env ]; then
    cp .env.example .env
    PUBLIC_IP="$(curl -s --max-time 3 https://checkip.amazonaws.com || true)"
    sed -i \
        -e "s#^ALLOWED_ORIGINS=.*#ALLOWED_ORIGINS=http://${PUBLIC_IP:-localhost}#" \
        -e "s#^WARMUP_MODEL=.*#WARMUP_MODEL=1#" \
        .env
    chmod 600 .env
    echo "    Created backend/.env - add your GROQ_API_KEY to it (nano backend/.env),"
    echo "    then run: sudo systemctl restart chat-exporter"
fi

echo "==> systemd service"
sed -e "s#__APP_DIR__#${APP_DIR}#g" -e "s#__USER__#${APP_USER}#g" \
    "$APP_DIR/deploy/systemd/chat-exporter.service" \
    | sudo tee /etc/systemd/system/chat-exporter.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable chat-exporter >/dev/null
sudo systemctl restart chat-exporter

echo "==> Nginx"
sudo mkdir -p "$WEB_ROOT"
# Owned by the login user so deploy/deploy-frontend.ps1 can upload without sudo.
sudo chown "$APP_USER": "$WEB_ROOT"
sudo cp "$APP_DIR/deploy/nginx/chat-exporter.conf" /etc/nginx/sites-available/chat-exporter
sudo ln -sf /etc/nginx/sites-available/chat-exporter /etc/nginx/sites-enabled/chat-exporter
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx >/dev/null
sudo systemctl reload-or-restart nginx

echo "==> Waiting for the API"
for _ in $(seq 1 30); do
    curl -fs http://127.0.0.1:8000/health >/dev/null && break
    sleep 2
done

if curl -fs http://127.0.0.1:8000/health >/dev/null; then
    echo "    API is up."
else
    echo "    API is not responding yet - check: journalctl -u chat-exporter -e"
fi

if [ ! -f "$WEB_ROOT/index.html" ]; then
    echo "    No frontend uploaded yet - run deploy/deploy-frontend.ps1 from your PC."
fi
