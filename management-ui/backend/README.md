# Management UI Backend

FastAPI backend for the local-ai-packaged management interface.

## Features

- JWT authentication with admin setup flow
- Docker container management via Docker SDK
- Service start/stop/restart/logs operations
- Configuration management (.env file editing)
- Secret generation for required credentials
- WebSocket-based real-time log streaming
- Dependency graph analysis from compose files

## Requirements

- Python 3.11+
- Docker (for container management)
- Access to Docker socket

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite:///./data/management.db` |
| `SECRET_KEY` | JWT signing key | `dev-secret-key` |
| `COMPOSE_BASE_PATH` | Path to docker-compose files | `../..` |

## Running

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Authentication
- `POST /api/auth/setup` - Create admin account (first run only)
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Services
- `GET /api/services` - List all services with status
- `POST /api/services/{name}/start` - Start a service
- `POST /api/services/{name}/stop` - Stop a service
- `POST /api/services/{name}/restart` - Restart a service
- `GET /api/services/dependencies` - Get dependency graph

### Configuration
- `GET /api/config` - Get current configuration
- `PUT /api/config` - Update configuration
- `POST /api/config/generate-secrets` - Generate missing secrets
- `GET /api/config/backups` - List configuration backups
- `POST /api/config/restore/{filename}` - Restore from backup

### Logs
- `GET /api/logs/{service}` - Get service logs (HTTP)
- `WS /api/logs/{service}/stream` - Stream logs (WebSocket)

### Setup
- `GET /api/setup/status` - Check setup status
- `POST /api/setup/complete` - Run full setup process

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/      # API route handlers
│   │   ├── deps.py      # Dependency injection
│   │   └── websocket.py # WebSocket handlers
│   ├── core/
│   │   ├── compose_parser.py    # Docker Compose file parsing
│   │   ├── dependency_graph.py  # Service dependency analysis
│   │   ├── docker_client.py     # Docker SDK wrapper
│   │   ├── env_manager.py       # .env file management
│   │   ├── secret_generator.py  # Cryptographic secret generation
│   │   └── security.py          # JWT and password hashing
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── config.py        # App configuration
│   ├── database.py      # Database setup
│   └── main.py          # FastAPI app
└── requirements.txt
```
