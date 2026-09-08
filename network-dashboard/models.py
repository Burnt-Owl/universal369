from pydantic import BaseModel


class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    is_dir: bool
    permissions: str
    modified: str


class SystemMetrics(BaseModel):
    cpu: float
    mem_used_mb: int
    mem_total_mb: int
    disk_used: str
    disk_total: str
    uptime: str
    load: str


class ServiceInfo(BaseModel):
    name: str
    status: str
    description: str


class ServiceAction(BaseModel):
    action: str  # start, stop, restart


class FileWriteRequest(BaseModel):
    path: str
    content: str


class PeerRegisterRequest(BaseModel):
    hostname: str
    address: str


class MessageRelay(BaseModel):
    sender: str
    content: str
    timestamp: str
