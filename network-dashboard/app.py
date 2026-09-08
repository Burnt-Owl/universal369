import asyncio
import json
import logging
import mimetypes
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Query, HTTPException
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

import config
import db
from models import ServiceAction, FileWriteRequest, PeerRegisterRequest, MessageRelay
from ssh_manager import ssh, SSHState
from heartbeat import dashboard_clients, chat_clients, broadcast_chat, start_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    log.info("Database initialized")

    db.upsert_peer(config.HOSTNAME, f"localhost:{config.DASHBOARD_PORT}", "online")

    await start_all()
    log.info("Network Dashboard running on port %d — heartbeat will handle VPS connection", config.DASHBOARD_PORT)

    yield

    ssh.disconnect()
    log.info("Shutdown complete")


app = FastAPI(title="Network Dashboard", lifespan=lifespan)


# ── REST: Status ─────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    return {
        "hostname": config.HOSTNAME,
        "vps_status": ssh.state.value,
        "vps_host": config.VPS_HOST,
        "vps_error": ssh.last_error,
        "dashboard_port": config.DASHBOARD_PORT,
    }


# ── REST: Services ───────────────────────────────────────────

@app.get("/api/services")
async def list_services():
    if ssh.state != SSHState.CONNECTED:
        raise HTTPException(503, "VPS not connected")
    loop = asyncio.get_event_loop()
    services = await loop.run_in_executor(None, ssh.list_services)
    return {"services": services}


@app.post("/api/services/{name}")
async def control_service(name: str, body: ServiceAction):
    if ssh.state != SSHState.CONNECTED:
        raise HTTPException(503, "VPS not connected")
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, ssh.service_action, name, body.action)
        return {"service": name, "action": body.action, "result": result.strip()}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── REST: Files ──────────────────────────────────────────────

@app.get("/api/files")
async def list_files(path: str = Query(default=config.SITE_PATH)):
    if ssh.state != SSHState.CONNECTED:
        raise HTTPException(503, "VPS not connected")
    try:
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, ssh.sftp_list, path)
        return {"path": path, "files": items}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, f"Path not found: {path}")


@app.get("/api/files/read")
async def read_file(path: str):
    if ssh.state != SSHState.CONNECTED:
        raise HTTPException(503, "VPS not connected")
    try:
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, ssh.sftp_read, path)
        return {"path": path, "content": content}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, f"File not found: {path}")


@app.put("/api/files/write")
async def write_file(body: FileWriteRequest):
    if ssh.state != SSHState.CONNECTED:
        raise HTTPException(503, "VPS not connected")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ssh.sftp_write, body.path, body.content)
        return {"path": body.path, "status": "saved"}
    except PermissionError as e:
        raise HTTPException(403, str(e))


@app.get("/api/files/download")
async def download_file(path: str):
    if ssh.state != SSHState.CONNECTED:
        raise HTTPException(503, "VPS not connected")
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, ssh.sftp_download, path)
        filename = os.path.basename(path)
        mime, _ = mimetypes.guess_type(filename)
        return Response(
            content=data,
            media_type=mime or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, f"File not found: {path}")


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...), destination: str = Query(...)):
    if ssh.state != SSHState.CONNECTED:
        raise HTTPException(503, "VPS not connected")
    try:
        data = await file.read()
        dest_path = os.path.join(destination, file.filename)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ssh.sftp_upload, dest_path, data)
        return {"path": dest_path, "size": len(data), "status": "uploaded"}
    except PermissionError as e:
        raise HTTPException(403, str(e))


@app.delete("/api/files")
async def delete_file(path: str):
    if ssh.state != SSHState.CONNECTED:
        raise HTTPException(503, "VPS not connected")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ssh.sftp_delete, path)
        return {"path": path, "status": "deleted"}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except FileNotFoundError:
        raise HTTPException(404, f"File not found: {path}")


@app.post("/api/files/mkdir")
async def create_directory(path: str = Query(...)):
    if ssh.state != SSHState.CONNECTED:
        raise HTTPException(503, "VPS not connected")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ssh.sftp_mkdir, path)
        return {"path": path, "status": "created"}
    except PermissionError as e:
        raise HTTPException(403, str(e))


# ── REST: Messages ───────────────────────────────────────────

@app.get("/api/messages")
async def get_messages(limit: int = 100, before: int | None = None):
    messages = db.get_messages(limit, before)
    return {"messages": messages}


@app.post("/api/messages/relay")
async def relay_message(body: MessageRelay):
    msg = db.insert_message(body.sender, body.content)
    await broadcast_chat({"type": "message", **msg})
    return {"status": "relayed"}


# ── REST: Peers ──────────────────────────────────────────────

@app.get("/api/peers")
async def list_peers():
    peers = db.get_peers()
    return {"peers": peers}


@app.post("/api/peers/register")
async def register_peer(body: PeerRegisterRequest):
    db.upsert_peer(body.hostname, body.address, "online")
    return {"status": "registered", "hostname": body.hostname}


# ── REST: Connection Log ─────────────────────────────────────

@app.get("/api/connection-log")
async def get_connection_log(limit: int = 50):
    logs = db.get_connection_log(limit)
    return {"logs": logs}


# ── WebSocket: Dashboard ─────────────────────────────────────

@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    await websocket.accept()
    dashboard_clients.add(websocket)
    try:
        await websocket.send_text(json.dumps({
            "type": "vps_status",
            "status": ssh.state.value,
        }))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        dashboard_clients.discard(websocket)


# ── WebSocket: Chat ──────────────────────────────────────────

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    hostname = None
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "join":
                hostname = data.get("hostname", "unknown")
                chat_clients[websocket] = hostname
                await broadcast_chat({
                    "type": "system",
                    "content": f"{hostname} joined the chat",
                })

            elif data.get("type") == "message" and hostname:
                content = data.get("content", "").strip()
                if content:
                    msg = db.insert_message(hostname, content)
                    await broadcast_chat({"type": "message", **msg})

    except WebSocketDisconnect:
        pass
    except json.JSONDecodeError:
        pass
    finally:
        chat_clients.pop(websocket, None)
        if hostname:
            await broadcast_chat({
                "type": "system",
                "content": f"{hostname} left the chat",
            })


# ── Static Files ─────────────────────────────────────────────

app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=config.DASHBOARD_PORT, reload=True)
