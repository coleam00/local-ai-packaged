# Stage 07: Log Streaming

## Summary
Add WebSocket-based real-time log streaming and a log viewer UI. After this stage, users can view live container logs.

## Prerequisites
- Stage 01-06 completed

## Deliverable
- WebSocket endpoints for log streaming
- Log viewer page with service selector
- Real-time log display with auto-scroll
- Log filtering and search
- Download logs

---

## Files to Create/Modify

### Backend
```
management-ui/backend/app/
├── api/
│   ├── websocket.py             # NEW
│   └── routes/
│       └── logs.py              # NEW
```

### Frontend
```
management-ui/frontend/src/
├── api/
│   └── websocket.ts             # NEW
├── hooks/
│   └── useWebSocket.ts          # NEW
├── components/
│   └── logs/
│       ├── LogViewer.tsx        # NEW
│       ├── LogStream.tsx        # NEW
│       └── LogFilter.tsx        # NEW
└── pages/
    └── Logs.tsx                 # NEW
```

---

## Task 1: Create WebSocket Handler (Backend)

**File**: `management-ui/backend/app/api/websocket.py`

```python
from fastapi import WebSocket, WebSocketDisconnect, Query
from typing import Optional
import asyncio
import json
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
                except:
                    dead_connections.add(connection)
            self.active_connections[channel] -= dead_connections

manager = ConnectionManager()

def verify_ws_token(token: str) -> bool:
    """Verify JWT token for WebSocket connections."""
    try:
        decode_token(token)
        return True
    except:
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
        # Send initial logs
        container = docker_client.get_container(service_name)
        if not container:
            await websocket.send_json({
                "type": "error",
                "message": f"Service {service_name} not found or not running"
            })
            return

        # Stream logs
        for log_line in docker_client.stream_logs(service_name, tail=tail):
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
        except:
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
            current_status = {c["service"]: {
                "status": c["status"],
                "health": c["health"]
            } for c in containers if c.get("service")}

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
        except:
            pass
```

---

## Task 2: Create Logs Routes (Backend)

**File**: `management-ui/backend/app/api/routes/logs.py`

```python
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from typing import Optional, List
from ...core.docker_client import DockerClient
from ...core.security import get_current_user
from ..deps import get_docker_client
from ..websocket import verify_ws_token, stream_service_logs, stream_all_status

router = APIRouter()

@router.get("/{service_name}")
async def get_logs(
    service_name: str,
    tail: int = Query(default=100, ge=1, le=10000),
    docker_client: DockerClient = Depends(get_docker_client),
    _: dict = Depends(get_current_user)
):
    """Get recent logs for a service (non-streaming)."""
    container = docker_client.get_container(service_name)
    if not container:
        return {"logs": [], "error": f"Service {service_name} not found"}

    try:
        container_obj = docker_client.client.containers.get(container["full_id"])
        logs = container_obj.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")
        lines = logs.strip().split("\n") if logs.strip() else []
        return {"logs": lines, "service": service_name, "count": len(lines)}
    except Exception as e:
        return {"logs": [], "error": str(e)}

@router.get("")
async def list_available_logs(
    docker_client: DockerClient = Depends(get_docker_client),
    _: dict = Depends(get_current_user)
):
    """List services that have logs available."""
    containers = docker_client.list_containers()
    available = [
        {
            "service": c["service"],
            "status": c["status"],
            "container_id": c["id"]
        }
        for c in containers
        if c.get("service") and c.get("status") == "running"
    ]
    return {"services": available}

@router.websocket("/ws/{service_name}")
async def websocket_logs(
    websocket: WebSocket,
    service_name: str,
    token: str = Query(...),
    tail: int = Query(default=100)
):
    """WebSocket endpoint for streaming logs."""
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    await stream_service_logs(websocket, service_name, tail)

@router.websocket("/ws/status")
async def websocket_status(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket endpoint for service status updates."""
    if not verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    await stream_all_status(websocket)
```

Update `management-ui/backend/app/api/routes/__init__.py`:
```python
from fastapi import APIRouter
from .auth import router as auth_router
from .services import router as services_router
from .config import router as config_router
from .logs import router as logs_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(services_router, prefix="/services", tags=["services"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])
```

---

## Task 3: Create WebSocket Hook (Frontend)

**File**: `management-ui/frontend/src/api/websocket.ts`

```typescript
import { getAuthToken } from './client';

export interface LogMessage {
  type: 'log' | 'error';
  service?: string;
  content?: string;
  message?: string;
}

export interface StatusMessage {
  type: 'status_update' | 'error';
  changes?: Array<{
    service: string;
    status: string;
    health: string;
  }>;
  message?: string;
}

export function createLogWebSocket(
  serviceName: string,
  onMessage: (msg: LogMessage) => void,
  onError?: (error: Event) => void,
  onClose?: () => void,
  tail: number = 100
): WebSocket | null {
  const token = getAuthToken();
  if (!token) return null;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const url = `${protocol}//${host}/api/logs/ws/${serviceName}?token=${token}&tail=${tail}`;

  const ws = new WebSocket(url);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch {
      onMessage({ type: 'log', content: event.data });
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.(error);
  };

  ws.onclose = () => {
    onClose?.();
  };

  return ws;
}

export function createStatusWebSocket(
  onMessage: (msg: StatusMessage) => void,
  onError?: (error: Event) => void
): WebSocket | null {
  const token = getAuthToken();
  if (!token) return null;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const url = `${protocol}//${host}/api/logs/ws/status?token=${token}`;

  const ws = new WebSocket(url);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse status message:', e);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.(error);
  };

  return ws;
}
```

**File**: `management-ui/frontend/src/hooks/useWebSocket.ts`

```typescript
import { useEffect, useRef, useState, useCallback } from 'react';
import { createLogWebSocket, LogMessage } from '../api/websocket';

interface UseLogStreamOptions {
  serviceName: string | null;
  tail?: number;
  enabled?: boolean;
}

export function useLogStream({ serviceName, tail = 100, enabled = true }: UseLogStreamOptions) {
  const [logs, setLogs] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  useEffect(() => {
    if (!serviceName || !enabled) {
      return;
    }

    setLogs([]);
    setError(null);

    const ws = createLogWebSocket(
      serviceName,
      (msg: LogMessage) => {
        if (msg.type === 'log' && msg.content) {
          setLogs((prev) => [...prev, msg.content!].slice(-5000)); // Keep last 5000 lines
        } else if (msg.type === 'error') {
          setError(msg.message || 'Unknown error');
        }
      },
      () => {
        setError('WebSocket connection error');
        setIsConnected(false);
      },
      () => {
        setIsConnected(false);
      },
      tail
    );

    if (ws) {
      wsRef.current = ws;
      ws.onopen = () => setIsConnected(true);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [serviceName, tail, enabled]);

  return { logs, isConnected, error, clearLogs };
}
```

---

## Task 4: Create Log Components (Frontend)

**File**: `management-ui/frontend/src/components/logs/LogFilter.tsx`

```typescript
import React from 'react';
import { Input } from '../common/Input';

interface LogFilterProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  autoScroll: boolean;
  onAutoScrollChange: (enabled: boolean) => void;
}

export const LogFilter: React.FC<LogFilterProps> = ({
  searchTerm,
  onSearchChange,
  autoScroll,
  onAutoScrollChange,
}) => {
  return (
    <div className="flex gap-4 items-center">
      <div className="flex-1">
        <input
          type="text"
          placeholder="Filter logs..."
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          className="input"
        />
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={autoScroll}
          onChange={(e) => onAutoScrollChange(e.target.checked)}
          className="rounded"
        />
        Auto-scroll
      </label>
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/logs/LogStream.tsx`

```typescript
import React, { useEffect, useRef, useMemo } from 'react';

interface LogStreamProps {
  logs: string[];
  searchTerm: string;
  autoScroll: boolean;
}

export const LogStream: React.FC<LogStreamProps> = ({ logs, searchTerm, autoScroll }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  const filteredLogs = useMemo(() => {
    if (!searchTerm) return logs;
    const term = searchTerm.toLowerCase();
    return logs.filter((log) => log.toLowerCase().includes(term));
  }, [logs, searchTerm]);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const highlightMatch = (text: string) => {
    if (!searchTerm) return text;
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    const parts = text.split(regex);
    return parts.map((part, i) =>
      part.toLowerCase() === searchTerm.toLowerCase() ? (
        <mark key={i} className="bg-yellow-200">{part}</mark>
      ) : (
        part
      )
    );
  };

  return (
    <div
      ref={containerRef}
      className="bg-gray-900 text-gray-100 font-mono text-sm p-4 rounded-lg h-[600px] overflow-y-auto"
    >
      {filteredLogs.length === 0 ? (
        <p className="text-gray-500">No logs available</p>
      ) : (
        filteredLogs.map((log, index) => (
          <div key={index} className="hover:bg-gray-800 py-0.5 whitespace-pre-wrap break-all">
            {highlightMatch(log)}
          </div>
        ))
      )}
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/logs/LogViewer.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { useLogStream } from '../../hooks/useWebSocket';
import { LogStream } from './LogStream';
import { LogFilter } from './LogFilter';
import { Button } from '../common/Button';
import { servicesApi } from '../../api/services';

interface ServiceOption {
  service: string;
  status: string;
}

export const LogViewer: React.FC = () => {
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [availableServices, setAvailableServices] = useState<ServiceOption[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [tail, setTail] = useState(100);

  const { logs, isConnected, error, clearLogs } = useLogStream({
    serviceName: selectedService,
    tail,
    enabled: !!selectedService,
  });

  useEffect(() => {
    const fetchServices = async () => {
      try {
        const response = await servicesApi.list();
        const running = response.services.filter((s) => s.status === 'running');
        setAvailableServices(running.map((s) => ({ service: s.name, status: s.status })));
        if (running.length > 0 && !selectedService) {
          setSelectedService(running[0].name);
        }
      } catch (e) {
        console.error('Failed to fetch services:', e);
      }
    };
    fetchServices();
  }, []);

  const handleDownload = () => {
    const blob = new Blob([logs.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedService}-logs.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Service Selector */}
      <div className="flex gap-4 items-center">
        <select
          value={selectedService || ''}
          onChange={(e) => setSelectedService(e.target.value)}
          className="input w-64"
        >
          <option value="" disabled>Select a service</option>
          {availableServices.map((svc) => (
            <option key={svc.service} value={svc.service}>
              {svc.service}
            </option>
          ))}
        </select>

        <select
          value={tail}
          onChange={(e) => setTail(Number(e.target.value))}
          className="input w-32"
        >
          <option value={50}>Last 50</option>
          <option value={100}>Last 100</option>
          <option value={500}>Last 500</option>
          <option value={1000}>Last 1000</option>
        </select>

        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}
          />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <div className="flex-1" />

        <Button variant="secondary" onClick={clearLogs}>
          Clear
        </Button>
        <Button variant="secondary" onClick={handleDownload} disabled={logs.length === 0}>
          Download
        </Button>
      </div>

      {/* Filter */}
      <LogFilter
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        autoScroll={autoScroll}
        onAutoScrollChange={setAutoScroll}
      />

      {/* Error Display */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded">
          {error}
        </div>
      )}

      {/* Log Display */}
      <LogStream logs={logs} searchTerm={searchTerm} autoScroll={autoScroll} />

      {/* Status Bar */}
      <div className="flex justify-between text-sm text-gray-500">
        <span>{logs.length} lines</span>
        <span>
          {searchTerm && `${logs.filter((l) => l.toLowerCase().includes(searchTerm.toLowerCase())).length} matches`}
        </span>
      </div>
    </div>
  );
};
```

---

## Task 5: Create Logs Page

**File**: `management-ui/frontend/src/pages/Logs.tsx`

```typescript
import React from 'react';
import { LogViewer } from '../components/logs/LogViewer';

export const Logs: React.FC = () => {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Logs</h2>
        <p className="text-gray-600">View real-time container logs</p>
      </div>

      <LogViewer />
    </div>
  );
};
```

Update App routes:
```typescript
import { Logs } from './pages/Logs';

// In routes:
<Route path="/logs" element={<Logs />} />
```

---

## Validation

### Test WebSocket
```bash
# Get token first
TOKEN="your-token"

# Test WebSocket with wscat
npm install -g wscat
wscat -c "ws://localhost:9000/api/logs/ws/redis?token=$TOKEN&tail=50"
```

### Test UI
1. Navigate to Logs page
2. Select a running service
3. See logs streaming in real-time
4. Test search/filter
5. Test auto-scroll toggle
6. Test clear and download
7. Switch between services

### Success Criteria
- [ ] Service selector shows running services
- [ ] Logs stream in real-time via WebSocket
- [ ] Connection status indicator works
- [ ] Filter/search works
- [ ] Auto-scroll works
- [ ] Clear logs works
- [ ] Download works
- [ ] Switching services reconnects

---

## Next Stage
Proceed to `08-dependency-visualization.md` to add dependency graph UI.
