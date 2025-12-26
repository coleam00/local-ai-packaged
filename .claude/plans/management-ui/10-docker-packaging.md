# Stage 10: Docker Packaging & Integration

## Summary
Create Docker images for the management UI and integrate it with the main docker-compose stack. After this stage, the management UI runs as a container alongside other services.

## Prerequisites
- Stage 01-09 completed

## Deliverable
- Multi-stage Dockerfile for combined backend+frontend
- docker-compose.management.yml integration
- Caddy routing for management UI
- Production-ready configuration

---

## Files to Create

```
management-ui/
├── Dockerfile                   # Combined multi-stage build
├── docker-compose.management.yml
├── nginx.conf                   # Frontend nginx config
├── supervisord.conf             # Process manager config
└── .dockerignore

# Root project modifications:
├── docker-compose.yml           # Add include for management
├── Caddyfile                    # Add management route
└── .env.example                 # Add MANAGEMENT_SECRET_KEY
```

---

## Task 1: Create .dockerignore

**File**: `management-ui/.dockerignore`

```
# Python
__pycache__
*.pyc
*.pyo
.pytest_cache
.coverage
htmlcov
.venv
venv
*.egg-info

# Node
node_modules
.npm
.cache

# IDE
.vscode
.idea
*.swp
*.swo

# Build outputs
dist
build
*.log

# Local data
data/
*.db
*.sqlite

# Git
.git
.gitignore
```

---

## Task 2: Create Backend Dockerfile

**File**: `management-ui/backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Create data directory
RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////data/management.db
ENV COMPOSE_BASE_PATH=/config

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Task 3: Create Frontend Dockerfile

**File**: `management-ui/frontend/Dockerfile`

```dockerfile
# Build stage
FROM node:20-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**File**: `management-ui/frontend/nginx.conf`

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    # API proxy
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Task 4: Create Combined Dockerfile

**File**: `management-ui/Dockerfile`

```dockerfile
# ======================
# Frontend Build Stage
# ======================
FROM node:20-alpine as frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ======================
# Backend Build Stage
# ======================
FROM python:3.11-slim as backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/app/ ./app/

# Copy frontend build
COPY --from=frontend-build /frontend/dist /var/www/html

# Copy nginx config for frontend
COPY nginx.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create directories
RUN mkdir -p /data /var/log/supervisor

# Environment
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////data/management.db
ENV COMPOSE_BASE_PATH=/config

EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9000/api/health || exit 1

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

---

## Task 5: Create Nginx Config

**File**: `management-ui/nginx.conf`

```nginx
server {
    listen 9000;
    server_name localhost;
    root /var/www/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    # API proxy to backend
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
}
```

---

## Task 6: Create Supervisor Config

**File**: `management-ui/supervisord.conf`

```ini
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:nginx]
command=nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:backend]
command=uvicorn app.main:app --host 127.0.0.1 --port 8000
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
environment=PYTHONUNBUFFERED="1"
```

---

## Task 7: Create Docker Compose for Management UI

**File**: `management-ui/docker-compose.management.yml`

```yaml
services:
  management-ui:
    build:
      context: ./management-ui
      dockerfile: Dockerfile
    image: localai-management:latest
    container_name: localai-management
    restart: unless-stopped
    ports:
      - "127.0.0.1:9000:9000"
    volumes:
      # Docker socket for container management
      - /var/run/docker.sock:/var/run/docker.sock:ro
      # Main project directory (read-only for compose files)
      - ./:/config:ro
      # Writable .env file
      - ./.env:/config/.env:rw
      # Backup directory
      - ./.env_backups:/config/.env_backups:rw
      # Persistent database
      - management-data:/data
    environment:
      - DATABASE_URL=sqlite:////data/management.db
      - COMPOSE_BASE_PATH=/config
      - SECRET_KEY=${MANAGEMENT_SECRET_KEY:-change-me-in-production}
    networks:
      - default
    labels:
      - "com.docker.compose.project=localai"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  management-data:

networks:
  default:
    name: localai_default
    external: true
```

---

## Task 8: Update Main Docker Compose

Add to the top of `docker-compose.yml`:

```yaml
include:
  - ./supabase/docker/docker-compose.yml
  - ./management-ui/docker-compose.management.yml  # Add this line
```

Or create a simple include file:

**File**: `docker-compose.management.yml` (in root)

```yaml
services:
  management-ui:
    build:
      context: ./management-ui
      dockerfile: Dockerfile
    image: localai-management:latest
    container_name: localai-management
    restart: unless-stopped
    ports:
      - "127.0.0.1:9000:9000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./:/config:ro
      - ./.env:/config/.env:rw
      - ./.env_backups:/config/.env_backups:rw
      - management-data:/data
    environment:
      - DATABASE_URL=sqlite:////data/management.db
      - COMPOSE_BASE_PATH=/config
      - SECRET_KEY=${MANAGEMENT_SECRET_KEY:-change-me-in-production}
    networks:
      - default
    labels:
      - "com.docker.compose.project=localai"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  management-data:
```

---

## Task 9: Update Caddyfile

Add to `Caddyfile`:

```
# Management UI
{$MANAGEMENT_HOSTNAME:-":9009"} {
    reverse_proxy management-ui:9000
}
```

Update `docker-compose.yml` Caddy service environment:

```yaml
caddy:
  environment:
    # ... existing vars ...
    - MANAGEMENT_HOSTNAME=${MANAGEMENT_HOSTNAME:-":9009"}
```

---

## Task 10: Update .env.example

Add to `.env.example`:

```
############
# Management UI
# Secret key for JWT tokens in the management interface
############
MANAGEMENT_SECRET_KEY=your-secure-secret-key-here

# Optional: Custom hostname for management UI (default: localhost:9009)
# MANAGEMENT_HOSTNAME=manage.yourdomain.com
```

---

## Task 11: Update docker-compose.override.private.yml

Add management UI port binding:

```yaml
services:
  management-ui:
    ports:
      - "127.0.0.1:9000:9000"
```

---

## Validation

### Build and Run
```bash
# Build the image
cd management-ui
docker build -t localai-management:latest .

# Or use docker-compose
docker compose -f docker-compose.management.yml build
docker compose -f docker-compose.management.yml up -d

# Check logs
docker logs localai-management

# Test health
curl http://localhost:9000/api/health
```

### Test Full Integration
```bash
# From project root
docker compose -p localai \
  -f docker-compose.yml \
  -f docker-compose.management.yml \
  --profile cpu \
  up -d

# Access management UI
open http://localhost:9000
```

### Success Criteria
- [ ] Docker image builds successfully
- [ ] Container starts and stays healthy
- [ ] Can access UI at localhost:9000
- [ ] API endpoints work (/api/health)
- [ ] Can control other containers from management UI
- [ ] WebSocket log streaming works
- [ ] Configuration changes persist
- [ ] Works with Caddy reverse proxy

---

## Production Checklist

Before deploying to production:

- [ ] Set strong `MANAGEMENT_SECRET_KEY` in .env
- [ ] Enable HTTPS via Caddy (set `MANAGEMENT_HOSTNAME`)
- [ ] Review Docker socket security implications
- [ ] Set up backup strategy for management database
- [ ] Configure log rotation
- [ ] Set resource limits in compose file
- [ ] Test disaster recovery (restore from backup)

---

## Summary

The Management UI is now fully containerized and integrated with the local-ai-packaged stack. Users can:

1. Access the UI at `http://localhost:9000` (or via Caddy)
2. Create admin account on first run
3. View and control all Docker services
4. Edit configuration with validation
5. Generate secure secrets
6. View real-time logs
7. Visualize service dependencies
8. Run guided setup for new installations

The UI runs as a sidecar container and can manage the entire stack, effectively replacing `start_services.py` with a modern web interface.
