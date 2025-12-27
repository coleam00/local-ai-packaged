from fastapi import WebSocket, WebSocketDisconnect
import asyncio
from ..core.docker_client import DockerClient
from ..core.security import decode_token
from ..config import settings


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)

    async def send_to_channel(self, channel: str, message: str):
        if channel in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_text(message)
                except Exception:
                    dead_connections.add(connection)
            self.active_connections[channel] -= dead_connections


manager = ConnectionManager()


def verify_ws_token(token: str) -> bool:
    """Verify JWT token for WebSocket connections."""
    try:
        decode_token(token)
        return True
    except Exception:
        return False


async def stream_service_logs(
    websocket: WebSocket,
    service_name: str,
    tail: int = 100
):
    """Stream logs for a specific service."""
    docker_client = DockerClient(
        project=settings.COMPOSE_PROJECT_NAME,
        base_path=settings.COMPOSE_BASE_PATH
    )

    try:
        # Check if container exists
        container = docker_client.get_container(service_name)
        if not container:
            await websocket.send_json({
                "type": "error",
                "message": f"Service {service_name} not found or not running"
            })
            return

        # Get the container for streaming
        container_obj = docker_client.client.containers.get(container["full_id"])

        # First, send recent logs (non-streaming)
        recent_logs = container_obj.logs(tail=tail, timestamps=False).decode("utf-8", errors="replace")
        for line in recent_logs.strip().split("\n"):
            if line:
                await websocket.send_json({
                    "type": "log",
                    "service": service_name,
                    "content": line.strip()
                })

        # Then stream new logs using asyncio.to_thread with a generator wrapper
        async def async_log_generator():
            """Wrap blocking log stream in async generator."""
            import queue
            import threading

            log_queue: queue.Queue[str | None] = queue.Queue()
            stop_flag = threading.Event()

            def read_logs():
                try:
                    # Stream only new logs (since=now, no tail)
                    for log in container_obj.logs(stream=True, follow=True, tail=0):
                        if stop_flag.is_set():
                            break
                        log_queue.put(log.decode("utf-8", errors="replace"))
                except Exception:
                    pass
                finally:
                    log_queue.put(None)

            thread = threading.Thread(target=read_logs, daemon=True)
            thread.start()

            try:
                while True:
                    try:
                        # Non-blocking get with timeout
                        line = await asyncio.to_thread(log_queue.get, timeout=1.0)
                        if line is None:
                            break
                        yield line
                    except Exception:
                        # Timeout or error, check if we should continue
                        continue
            finally:
                stop_flag.set()

        async for log_line in async_log_generator():
            await websocket.send_json({
                "type": "log",
                "service": service_name,
                "content": log_line.strip()
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass


async def stream_all_status(websocket: WebSocket):
    """Stream status updates for all services."""
    docker_client = DockerClient(
        project=settings.COMPOSE_PROJECT_NAME,
        base_path=settings.COMPOSE_BASE_PATH
    )

    previous_status = {}

    try:
        while True:
            containers = docker_client.list_containers()
            current_status = {
                c["service"]: {
                    "status": c["status"],
                    "health": c["health"]
                }
                for c in containers if c.get("service")
            }

            # Detect changes
            changes = []
            for service, status in current_status.items():
                if service not in previous_status or previous_status[service] != status:
                    changes.append({
                        "service": service,
                        **status
                    })

            if changes:
                await websocket.send_json({
                    "type": "status_update",
                    "changes": changes
                })

            previous_status = current_status
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
