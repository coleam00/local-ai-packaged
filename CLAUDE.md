# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a self-hosted AI package that combines multiple open-source AI tools into a unified Docker Compose stack. The main components include n8n for AI workflows, Open WebUI for chat interfaces, Ollama for local LLMs, Supabase for database/auth, and several supporting services.

## Common Development Commands

### Starting Services
```bash
# Start with CPU support (default)
python start_services.py --profile cpu

# Start with Nvidia GPU support  
python start_services.py --profile gpu-nvidia

# Start with AMD GPU support
python start_services.py --profile gpu-amd

# Start without Ollama (for Mac users running Ollama locally)
python start_services.py --profile none

# Start for production deployment (closes most ports)
python start_services.py --profile gpu-nvidia --environment public
```

### Managing Docker Services
```bash
# Stop all services
docker compose -p localai -f docker-compose.yml --profile <profile> down

# View logs for specific service
docker compose -p localai logs -f <service-name>

# Pull latest container versions
docker compose -p localai -f docker-compose.yml --profile <profile> pull
```

### Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Generate secure keys (Linux/Mac)
openssl rand -hex 32

# Generate secure keys (Python alternative)
python -c "import secrets; print(secrets.token_hex(32))"
```

## Architecture

### Core Services Architecture
- **n8n** (port 5678): Low-code workflow automation platform with AI capabilities
- **Open WebUI** (port 3000): ChatGPT-like interface for interacting with local models
- **Ollama** (port 11434): Local LLM inference server
- **Supabase Stack**: PostgreSQL database, authentication, and admin dashboard
- **Qdrant** (port 6333): Vector database for RAG workflows
- **Flowise** (port 3001): Visual AI agent builder
- **Neo4j** (port 7474): Graph database for knowledge graphs
- **Langfuse** (port 3002): LLM observability and analytics
- **SearXNG** (port 8080): Privacy-focused metasearch engine
- **Caddy**: Reverse proxy with automatic HTTPS

### Service Dependencies
1. **Supabase services** start first (PostgreSQL, Kong, Auth, etc.)
2. **Local AI services** start after Supabase initialization
3. **n8n-import** runs once to import workflows/credentials
4. **ollama-pull-llama** services download default models (qwen2.5:7b, nomic-embed-text)

### Data Persistence
- **Volumes**: All services use named Docker volumes for persistence
- **Shared folder**: `/data/shared` mounted in n8n for file system access
- **Backup workflows**: Pre-configured n8n workflows in `n8n/backup/workflows/`

### Network Configuration
- **Project name**: All services use `localai` Docker Compose project
- **Internal networking**: Services communicate via container names
- **External access**: Caddy provides reverse proxy with optional SSL/domains

## Key Configuration Files

### Environment Variables (.env)
Required secrets for all services including:
- N8N encryption keys
- Supabase PostgreSQL and JWT secrets  
- Neo4j authentication
- Langfuse credentials
- Optional production domain configuration
- **PORTS section**: Centralized port configuration for all services to avoid conflicts

### Docker Compose Structure
- **Base**: `docker-compose.yml` - core service definitions
- **Profiles**: CPU, GPU-Nvidia, GPU-AMD variants for Ollama
- **Overrides**: Public/private network configurations
- **Supabase**: Separate compose file in `supabase/docker/`

### Service Templates (x-* anchors)
- **x-n8n**: Common n8n service configuration
- **x-ollama**: Ollama service variants with GPU support
- **x-init-ollama**: Model downloading initialization

## Development Workflow

### Initial Setup
1. Clone repository and copy `.env.example` to `.env`
2. Generate secure values for all required environment variables
3. Run `python start_services.py` with appropriate profile
4. Access services at their respective localhost ports

### Working with n8n
- Access at http://localhost:5678
- Pre-configured workflows automatically imported
- Credentials needed for Ollama, PostgreSQL, Qdrant integrations
- Shared folder at `/data/shared` for file operations

### Working with Open WebUI
- Access at http://localhost:3000  
- Install n8n pipe function from `n8n_pipe.py`
- Configure webhook URL from n8n workflow
- Enables chat interface with n8n agent workflows

### Production Deployment
- Set domain environment variables in `.env`
- Use `--environment public` to close non-essential ports
- Configure DNS A records for subdomains
- Caddy handles automatic Let's Encrypt certificates

## Important Implementation Details

### Port Configuration
- All service ports are centralized in the `.env` file PORTS section
- External ports (for host access) are configurable via environment variables
- Internal ports (for inter-service communication) use defaults with overrides
- Bind IP address can be configured for private environment (default: 192.168.5.10)
- Caddy proxy ports (80/443) are configurable for custom deployments

### start_services.py Script
- Uses external Supabase installation at `/root/supabase-localai`
- Generates SearXNG secret keys per platform
- Handles Docker Compose cap_drop modifications for SearXNG first run
- Manages unified project lifecycle with proper startup ordering

### Security Considerations
- Default configuration includes security capabilities restrictions
- SearXNG requires temporary cap_drop removal on first run
- Production mode closes all ports except 80/443
- Environment variables must be properly secured for production

### Model Management
- Default models: qwen2.5:7b-instruct-q4_K_M, nomic-embed-text
- Ollama storage persisted in named volume
- Models automatically downloaded on first startup
- Context length and performance settings configurable via environment

### Troubleshooting Areas
- Supabase pooler issues with special characters in passwords
- GPU support requires proper Docker/driver configuration
- Mac users need host.docker.internal configuration for local Ollama
- SearXNG first-run permissions requirements