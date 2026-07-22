#!/usr/bin/env bash
set -e

# ── Network Dashboard — Fleet Node Setup ────────────────────
# Run this on any machine to join the fleet.
# Usage: chmod +x setup.sh && ./setup.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DASHBOARD_PORT=8369

echo "═══════════════════════════════════════════"
echo "  NETWORK DASHBOARD — Fleet Node Setup"
echo "═══════════════════════════════════════════"
echo ""

# ── 1. Check Python ─────────────────────────────────────────
echo "[1/6] Checking Python..."
if command -v python3 &>/dev/null; then
    PY=$(command -v python3)
    PY_VER=$($PY --version 2>&1 | awk '{print $2}')
    echo "  Found Python $PY_VER at $PY"
else
    echo "  ERROR: Python 3 not found. Install it first:"
    echo "    sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

# ── 2. Create venv and install deps ─────────────────────────
echo "[2/6] Setting up virtual environment..."
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    $PY -m venv "$SCRIPT_DIR/.venv"
    echo "  Created .venv"
else
    echo "  .venv already exists"
fi

source "$SCRIPT_DIR/.venv/bin/activate"
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "  Dependencies installed"

# ── 3. Configure .env ───────────────────────────────────────
echo "[3/6] Configuring environment..."
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo ""
    echo "  .env created from template. You should edit it:"
    echo "    nano $SCRIPT_DIR/.env"
    echo ""
    echo "  Key settings:"
    echo "    VPS_HOST     — Your VPS IP (default: 187.77.208.156)"
    echo "    VPS_PORT     — SSH port (default: 2222)"
    echo "    SSH_KEY_PATH — Path to your SSH private key"
    echo "    KNOWN_PEERS  — Other fleet nodes (e.g. 192.168.1.10:8369)"
    echo ""
else
    echo "  .env already exists, keeping it"
fi

# ── 4. Test the server starts ────────────────────────────────
echo "[4/6] Testing server startup..."
cd "$SCRIPT_DIR"
timeout 5 "$SCRIPT_DIR/.venv/bin/python" -c "
import sys; sys.path.insert(0, '.')
from app import app
print('  Server imports OK — all good')
" 2>/dev/null || echo "  WARNING: Import test failed, check requirements"

# ── 5. Install systemd service (auto-start on boot) ─────────
echo "[5/6] Setting up auto-start service..."
SERVICE_FILE="/etc/systemd/system/network-dashboard.service"

if [ "$EUID" -eq 0 ] || command -v sudo &>/dev/null; then
    RUNNER=${SUDO_USER:-$(whoami)}
    cat > /tmp/network-dashboard.service <<UNIT
[Unit]
Description=Network Dashboard — Fleet Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUNNER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port $DASHBOARD_PORT
Restart=always
RestartSec=5
Environment=PATH=$SCRIPT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
UNIT

    if [ "$EUID" -eq 0 ]; then
        cp /tmp/network-dashboard.service "$SERVICE_FILE"
        systemctl daemon-reload
        systemctl enable network-dashboard
        echo "  Service installed and enabled"
        echo "  Start now with: sudo systemctl start network-dashboard"
    else
        sudo cp /tmp/network-dashboard.service "$SERVICE_FILE"
        sudo systemctl daemon-reload
        sudo systemctl enable network-dashboard
        echo "  Service installed and enabled"
        echo "  Start now with: sudo systemctl start network-dashboard"
    fi
    rm -f /tmp/network-dashboard.service
else
    echo "  SKIP: No sudo access. To install manually:"
    echo "    sudo cp the service file to /etc/systemd/system/"
fi

# ── 6. Tailscale check ──────────────────────────────────────
echo "[6/6] Checking Tailscale..."
if command -v tailscale &>/dev/null; then
    TS_IP=$(tailscale ip -4 2>/dev/null || echo "not connected")
    echo "  Tailscale installed — IP: $TS_IP"
    echo "  Other fleet nodes can reach this machine at $TS_IP:$DASHBOARD_PORT"
else
    echo "  Tailscale not installed (optional but recommended for remote access)"
    echo "  Install: curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up"
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  SETUP COMPLETE"
echo "═══════════════════════════════════════════"
echo ""
echo "  Quick start:"
echo "    cd $SCRIPT_DIR"
echo "    source .venv/bin/activate"
echo "    python app.py"
echo ""
echo "  Then open: http://localhost:$DASHBOARD_PORT"
echo ""
echo "  Or run as a service:"
echo "    sudo systemctl start network-dashboard"
echo "    sudo systemctl status network-dashboard"
echo ""
echo "  To connect to other fleet nodes, add their IPs to .env:"
echo "    KNOWN_PEERS=192.168.1.10:8369,192.168.1.20:8369"
echo ""
