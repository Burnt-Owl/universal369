import asyncio
import json
import logging
from datetime import datetime, timezone

import db
from ssh_manager import ssh, SSHState
import config

log = logging.getLogger("heartbeat")

dashboard_clients: set = set()
chat_clients: dict = {}


async def broadcast_dashboard(data: dict):
    msg = json.dumps(data)
    dead = set()
    for ws in dashboard_clients.copy():
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    dashboard_clients.difference_update(dead)


async def broadcast_chat(data: dict):
    msg = json.dumps(data)
    dead = []
    for ws in list(chat_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        chat_clients.pop(ws, None)


async def vps_heartbeat():
    last_state = None
    while True:
        try:
            if ssh.state == SSHState.CONNECTED:
                try:
                    ssh.exec("echo ok", timeout=5)
                    new_state = SSHState.CONNECTED
                except Exception:
                    new_state = SSHState.DISCONNECTED
                    db.log_connection("vps", "disconnected")
                    log.warning("VPS heartbeat failed, reconnecting...")
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, ssh.reconnect)
                    new_state = ssh.state
                    if new_state == SSHState.CONNECTED:
                        db.log_connection("vps", "reconnected")
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, ssh.reconnect)
                new_state = ssh.state
                if new_state == SSHState.CONNECTED:
                    db.log_connection("vps", "connected")

            if new_state != last_state:
                last_state = new_state
                await broadcast_dashboard({
                    "type": "vps_status",
                    "status": new_state.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            log.error("Heartbeat error: %s", e)

        await asyncio.sleep(config.HEARTBEAT_INTERVAL)


async def metrics_loop():
    while True:
        try:
            if ssh.state == SSHState.CONNECTED:
                loop = asyncio.get_event_loop()
                metrics = await loop.run_in_executor(None, ssh.get_metrics)
                await broadcast_dashboard({"type": "metrics", **metrics})
        except Exception as e:
            log.error("Metrics error: %s", e)

        await asyncio.sleep(config.METRICS_INTERVAL)


async def peer_heartbeat():
    try:
        import httpx
    except ImportError:
        log.warning("httpx not installed — peer heartbeat disabled")
        return
    while True:
        try:
            peers = db.get_peers()
            async with httpx.AsyncClient(timeout=3) as client:
                for peer in peers:
                    try:
                        resp = await client.get(f"http://{peer['address']}/api/status")
                        if resp.status_code == 200:
                            db.update_peer_status(peer["hostname"], "online")
                        else:
                            db.update_peer_status(peer["hostname"], "offline")
                    except Exception:
                        db.update_peer_status(peer["hostname"], "offline")

            updated_peers = db.get_peers()
            await broadcast_dashboard({
                "type": "peers",
                "peers": updated_peers,
            })
        except ImportError:
            pass
        except Exception as e:
            log.error("Peer heartbeat error: %s", e)

        await asyncio.sleep(config.HEARTBEAT_INTERVAL)


async def start_all():
    asyncio.create_task(vps_heartbeat())
    asyncio.create_task(metrics_loop())
    asyncio.create_task(peer_heartbeat())
    log.info("Heartbeat system started")
