import logging
import os
import stat
import time
from enum import Enum
from io import BytesIO
from pathlib import Path

import paramiko

import config

log = logging.getLogger("ssh_manager")


class SSHState(str, Enum):
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"


class SSHManager:
    def __init__(self):
        self.client: paramiko.SSHClient | None = None
        self.sftp: paramiko.SFTPClient | None = None
        self.state = SSHState.DISCONNECTED
        self._backoff = 0
        self._last_error = ""

    @property
    def last_error(self):
        return self._last_error

    def connect(self) -> bool:
        if self.state == SSHState.CONNECTED:
            return True

        key_path = os.path.expanduser(config.SSH_KEY_PATH)
        if not os.path.exists(key_path):
            self._last_error = f"SSH key not found: {key_path}"
            self.state = SSHState.DISCONNECTED
            log.warning("SSH key not found at %s — VPS features disabled until key is available", key_path)
            return False

        self.state = SSHState.CONNECTING
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=config.VPS_HOST,
                port=config.VPS_PORT,
                username=config.VPS_USER,
                key_filename=key_path,
                timeout=8,
                banner_timeout=8,
                auth_timeout=8,
            )
            self.sftp = self.client.open_sftp()
            self.state = SSHState.CONNECTED
            self._backoff = 0
            self._last_error = ""
            log.info("SSH connected to %s:%s", config.VPS_HOST, config.VPS_PORT)
            return True
        except FileNotFoundError:
            self._last_error = f"SSH key not found: {key_path}"
            self.state = SSHState.DISCONNECTED
            log.error("SSH key file not found: %s", key_path)
            return False
        except paramiko.AuthenticationException as e:
            self._last_error = f"Authentication failed: {e}"
            self.state = SSHState.DISCONNECTED
            log.error("SSH auth failed: %s", e)
            return False
        except Exception as e:
            self._last_error = str(e)
            self.state = SSHState.DISCONNECTED
            log.error("SSH connection failed: %s", e)
            return False

    def disconnect(self):
        try:
            if self.sftp:
                self.sftp.close()
            if self.client:
                self.client.close()
        except Exception:
            pass
        self.sftp = None
        self.client = None
        self.state = SSHState.DISCONNECTED

    def get_reconnect_delay(self) -> int:
        delays = [2, 4, 8, 16, 30, 60]
        return delays[min(self._backoff, len(delays) - 1)]

    def reconnect(self) -> bool:
        self.disconnect()
        self._backoff += 1
        return self.connect()

    def exec(self, cmd: str, timeout: int = 15) -> str:
        if self.state != SSHState.CONNECTED or not self.client:
            raise ConnectionError("SSH not connected")
        try:
            transport = self.client.get_transport()
            if not transport or not transport.is_active():
                raise ConnectionError("SSH transport inactive")
            _, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
            output = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            if err and not output:
                return err
            return output
        except Exception as e:
            self.state = SSHState.DISCONNECTED
            raise ConnectionError(f"SSH exec failed: {e}") from e

    def _validate_path(self, path: str):
        resolved = os.path.normpath(path)
        root = os.path.normpath(config.SITE_PATH)
        if not resolved.startswith(root):
            raise PermissionError(f"Path {path} is outside allowed root {root}")
        return resolved

    def sftp_list(self, path: str) -> list[dict]:
        if not self.sftp:
            raise ConnectionError("SFTP not connected")
        path = self._validate_path(path)
        items = []
        for attr in self.sftp.listdir_attr(path):
            is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
            perms = stat.filemode(attr.st_mode) if attr.st_mode else "----------"
            items.append({
                "name": attr.filename,
                "path": os.path.join(path, attr.filename),
                "size": attr.st_size or 0,
                "is_dir": is_dir,
                "permissions": perms,
                "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(attr.st_mtime or 0)),
            })
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return items

    def sftp_read(self, path: str) -> str:
        if not self.sftp:
            raise ConnectionError("SFTP not connected")
        path = self._validate_path(path)
        with self.sftp.open(path, "r") as f:
            return f.read().decode("utf-8", errors="replace")

    def sftp_write(self, path: str, content: str):
        if not self.sftp:
            raise ConnectionError("SFTP not connected")
        path = self._validate_path(path)
        with self.sftp.open(path, "w") as f:
            f.write(content.encode("utf-8"))

    def sftp_download(self, path: str) -> bytes:
        if not self.sftp:
            raise ConnectionError("SFTP not connected")
        path = self._validate_path(path)
        buf = BytesIO()
        self.sftp.getfo(path, buf)
        buf.seek(0)
        return buf.read()

    def sftp_upload(self, path: str, data: bytes):
        if not self.sftp:
            raise ConnectionError("SFTP not connected")
        path = self._validate_path(path)
        buf = BytesIO(data)
        self.sftp.putfo(buf, path)
        self.exec(f"chmod 644 {path}")

    def sftp_delete(self, path: str):
        if not self.sftp:
            raise ConnectionError("SFTP not connected")
        path = self._validate_path(path)
        self.sftp.remove(path)

    def sftp_mkdir(self, path: str):
        if not self.sftp:
            raise ConnectionError("SFTP not connected")
        path = self._validate_path(path)
        self.sftp.mkdir(path)
        self.exec(f"chmod 755 {path}")

    def get_metrics(self) -> dict:
        raw = self.exec(
            'echo "CPU:$(top -bn1 | grep "Cpu(s)" | awk \'{print $2}\')";'
            'echo "MEM:$(free -m | awk \'/Mem:/{print $3"/"$2}\')";'
            'echo "DISK:$(df -h / | awk \'NR==2{print $3"/"$2}\')";'
            'echo "UPTIME:$(uptime -p)";'
            'echo "LOAD:$(cat /proc/loadavg | awk \'{print $1,$2,$3}\')"'
        )
        metrics = {"cpu": 0.0, "mem_used_mb": 0, "mem_total_mb": 0,
                    "disk_used": "0", "disk_total": "0", "uptime": "unknown", "load": "0"}
        for line in raw.strip().split("\n"):
            if line.startswith("CPU:"):
                try:
                    metrics["cpu"] = float(line.split(":")[1])
                except (ValueError, IndexError):
                    pass
            elif line.startswith("MEM:"):
                try:
                    parts = line.split(":")[1].split("/")
                    metrics["mem_used_mb"] = int(parts[0])
                    metrics["mem_total_mb"] = int(parts[1])
                except (ValueError, IndexError):
                    pass
            elif line.startswith("DISK:"):
                try:
                    parts = line.split(":")[1].split("/")
                    metrics["disk_used"] = parts[0]
                    metrics["disk_total"] = parts[1]
                except (ValueError, IndexError):
                    pass
            elif line.startswith("UPTIME:"):
                metrics["uptime"] = line.split(":", 1)[1].strip()
            elif line.startswith("LOAD:"):
                metrics["load"] = line.split(":", 1)[1].strip()
        return metrics

    def list_services(self) -> list[dict]:
        raw = self.exec(
            "systemctl list-units --type=service --no-pager --plain --no-legend "
            "| awk '{print $1, $3, $4}'"
        )
        services = []
        for line in raw.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(None, 2)
            if len(parts) < 2:
                continue
            name = parts[0].replace(".service", "")
            svc_status = parts[1] if len(parts) > 1 else "unknown"
            desc = parts[2] if len(parts) > 2 else ""
            if name in config.ALLOWED_SERVICES:
                services.append({"name": name, "status": svc_status, "description": desc})
        return services

    def service_action(self, name: str, action: str) -> str:
        if name not in config.ALLOWED_SERVICES:
            raise PermissionError(f"Service '{name}' is not in the allowed list")
        if action not in ("start", "stop", "restart", "status"):
            raise ValueError(f"Invalid action: {action}")
        return self.exec(f"systemctl {action} {name} 2>&1")


ssh = SSHManager()
