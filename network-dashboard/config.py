import os
import socket
from pathlib import Path
from dotenv import load_dotenv

_VAULT = Path.home() / ".network-dashboard" / ".env"
_LOCAL = Path(__file__).parent / ".env"

load_dotenv(_VAULT)
load_dotenv(_LOCAL, override=False)

VPS_HOST = os.getenv("VPS_HOST", "187.77.208.156")
VPS_PORT = int(os.getenv("VPS_PORT", "2222"))
VPS_USER = os.getenv("VPS_USER", "root")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", str(Path.home() / ".ssh" / "id_ed25519"))
SITE_PATH = os.getenv("SITE_PATH", "/home/universal369.com/public_html/")

DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8369"))
HOSTNAME = os.getenv("HOSTNAME", "") or socket.gethostname()

KNOWN_PEERS = [p.strip() for p in os.getenv("KNOWN_PEERS", "").split(",") if p.strip()]

HEARTBEAT_INTERVAL = 10
METRICS_INTERVAL = 5

ALLOWED_SERVICES = [
    "lsws", "litespeed", "nginx", "apache2", "httpd",
    "mysql", "mariadb", "postgresql", "redis-server",
    "sshd", "fail2ban", "ufw", "cron",
    "docker", "containerd",
]

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "dashboard.db"
