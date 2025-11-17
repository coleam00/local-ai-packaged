# Guia Completo: Self-Hosting do Plane com Banco de Dados Existente

## Visão Geral

Este guia detalha a integração do **Plane** (gerenciamento de projetos open-source) com a infraestrutura existente do projeto AI-Stack, reutilizando o banco de dados PostgreSQL e integrando com a metodologia BMAD via Model Context Protocol (MCP).

## Arquitetura de Integração

```
┌─────────────────────────────────────────────────────────────┐
│                    AI-STACK ECOSYSTEM                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐    ┌─────────────┐ │
│  │ PostgreSQL   │◄─────┤  Plane API   │◄───┤ Plane Web   │ │
│  │ (Existente)  │      │ Backend      │    │ Interface   │ │
│  │ - ai_rag     │      │              │    │ :3002       │ │
│  │ - plane_db   │      └──────┬───────┘    └─────────────┘ │
│  └──────────────┘             │                             │
│         ▲                     │                             │
│         │                     ▼                             │
│  ┌──────┴───────┐      ┌──────────────┐                    │
│  │ Neo4j        │      │ Plane Worker │                    │
│  │ (Graphs)     │      │ + Beat Worker│                    │
│  └──────────────┘      └──────────────┘                    │
│                                                              │
│  ┌──────────────┐      ┌──────────────┐    ┌─────────────┐ │
│  │ LightRAG     │      │ n8n          │    │ Plane MCP   │ │
│  │ :9621        │      │ :5678        │    │ Server      │ │
│  └──────────────┘      └──────────────┘    └──────┬──────┘ │
│                                                    │         │
│                                                    ▼         │
│                                            ┌───────────────┐ │
│                                            │ Claude Code   │ │
│                                            │ + BMAD Agents │ │
│                                            └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Principais:

PostgreSQL Existente: Criação de banco plane_db separado usando o mesmo servidor PostgreSQL do projeto (container ai-postgres)​

Plane API Backend: Serviço principal que gerencia projetos, issues e workflows​

Plane Web Interface: Interface Next.js acessível em http://localhost:3002​

Plane Workers: Serviços assíncronos para tarefas em background e agendadas​

Redis Dedicado: Cache e fila de mensagens para o Plane​

MinIO: Storage S3-compatible para uploads de arquivos​

Plane MCP Server: Ponte entre Claude Code e API do Plane para automação via agentes BMAD​​
---

## 1. Configuração do Docker Compose

### 1.1 Adicionar Serviços do Plane ao `docker-compose.yml`

Adicione os seguintes serviços ao seu arquivo `docker-compose.yml` existente:

```yaml
services:
  # ... serviços existentes (postgres, neo4j, lightrag, n8n, etc.)

  # Plane Web Interface
  plane-web:
    image: makeplane/plane-frontend:latest
    container_name: ai-plane-web
    restart: always
    env_file:
      - .env.plane.env
    environment:
      - NEXT_PUBLIC_API_BASE_URL=http://plane-api:8000
      - NEXT_PUBLIC_DEPLOY_URL=http://localhost:3002
    ports:
      - "3002:3000"
    networks:
      ai_net:
        ipv4_address: 172.31.0.60
    depends_on:
      plane-api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Plane API Backend
  plane-api:
    image: makeplane/plane-backend:latest
    container_name: ai-plane-api
    restart: always
    env_file:
      - .env.plane.env
    environment:
      # Database - Usando PostgreSQL existente
      - DATABASE_URL=postgresql://rag_user:${DB_PASSWORD}@postgres:5432/plane_db
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=plane_db
      - POSTGRES_USER=rag_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_PORT=5432
      
      # Redis
      - REDIS_URL=redis://plane-redis:6379/
      
      # Application Settings
      - SECRET_KEY=${PLANE_SECRET_KEY}
      - WEB_URL=http://localhost:3002
      - CORS_ALLOWED_ORIGINS=http://localhost:3002
      
      # Storage (MinIO)
      - USE_MINIO=1
      - AWS_REGION=us-east-1
      - AWS_ACCESS_KEY_ID=${PLANE_AWS_ACCESS_KEY}
      - AWS_SECRET_ACCESS_KEY=${PLANE_AWS_SECRET_KEY}
      - AWS_S3_ENDPOINT_URL=http://plane-minio:9000
      - AWS_S3_BUCKET_NAME=plane-uploads
    volumes:
      - ./plane-logs:/code/plane/logs
    networks:
      ai_net:
        ipv4_address: 172.31.0.61
    depends_on:
      postgres:
        condition: service_healthy
      plane-redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 90s

  # Plane Worker (tarefas assíncronas)
  plane-worker:
    image: makeplane/plane-backend:latest
    container_name: ai-plane-worker
    restart: always
    command: ./bin/worker
    env_file:
      - .env.plane.env
    environment:
      - DATABASE_URL=postgresql://rag_user:${DB_PASSWORD}@postgres:5432/plane_db
      - REDIS_URL=redis://plane-redis:6379/
      - SECRET_KEY=${PLANE_SECRET_KEY}
    networks:
      ai_net:
        ipv4_address: 172.31.0.62
    depends_on:
      plane-api:
        condition: service_healthy

  # Plane Beat Worker (tarefas agendadas)
  plane-beat-worker:
    image: makeplane/plane-backend:latest
    container_name: ai-plane-beat-worker
    restart: always
    command: ./bin/beat
    env_file:
      - .env.plane.env
    environment:
      - DATABASE_URL=postgresql://rag_user:${DB_PASSWORD}@postgres:5432/plane_db
      - REDIS_URL=redis://plane-redis:6379/
      - SECRET_KEY=${PLANE_SECRET_KEY}
    networks:
      ai_net:
        ipv4_address: 172.31.0.63
    depends_on:
      plane-api:
        condition: service_healthy

  # Redis dedicado para Plane
  plane-redis:
    image: redis:7.2-alpine
    container_name: ai-plane-redis
    restart: always
    volumes:
      - plane_redis_data:/data
    networks:
      ai_net:
        ipv4_address: 172.31.0.64
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # MinIO para storage de arquivos
  plane-minio:
    image: minio/minio:latest
    container_name: ai-plane-minio
    restart: always
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${PLANE_MINIO_ROOT_USER}
      - MINIO_ROOT_PASSWORD=${PLANE_MINIO_ROOT_PASSWORD}
    volumes:
      - plane_minio_data:/data
    ports:
      - "9001:9001"  # Console MinIO
    networks:
      ai_net:
        ipv4_address: 172.31.0.65
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  # ... volumes existentes
  plane_redis_data:
    driver: local
  plane_minio_data:
    driver: local
```

---

## 2. Configuração de Variáveis de Ambiente

### 2.1 Adicionar ao `.env` principal

```bash
# --- Plane Configuration ---
PLANE_SECRET_KEY=your-super-secret-plane-key-change-me
PLANE_AWS_ACCESS_KEY=plane-minio-access
PLANE_AWS_SECRET_KEY=plane-minio-secret-key-change-me
PLANE_MINIO_ROOT_USER=plane-minio-access
PLANE_MINIO_ROOT_PASSWORD=plane-minio-secret-key-change-me

# Plane API
PLANE_API_BASE_URL=http://localhost:3002
PLANE_API_KEY=  # Será gerado após primeiro acesso
PLANE_WORKSPACE_SLUG=ai-automation
```

**⚠️ IMPORTANTE**: Gere uma SECRET_KEY segura com:
```bash
openssl rand -hex 32
```

### 2.2 Criar arquivo `.env.plane.env`

```bash
# /ai-stack/.env.plane.env
# =======================================================
# ==      .ENV ESPECÍFICO PARA O PLANE                 ==
# =======================================================

# --- Database Configuration (PostgreSQL Existente) ---
DATABASE_URL=postgresql://rag_user:${DB_PASSWORD}@postgres:5432/plane_db
POSTGRES_HOST=postgres
POSTGRES_DB=plane_db
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_PORT=5432

# --- Redis Configuration ---
REDIS_URL=redis://plane-redis:6379/

# --- Application Settings ---
SECRET_KEY=${PLANE_SECRET_KEY}
WEB_URL=http://localhost:3002
CORS_ALLOWED_ORIGINS=http://localhost:3002

# --- Storage Configuration (MinIO) ---
USE_MINIO=1
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=${PLANE_AWS_ACCESS_KEY}
AWS_SECRET_ACCESS_KEY=${PLANE_AWS_SECRET_KEY}
AWS_S3_ENDPOINT_URL=http://plane-minio:9000
AWS_S3_BUCKET_NAME=plane-uploads

# --- Email Configuration (Opcional) ---
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# --- Plane Features ---
ENABLE_SIGNUP=true
ENABLE_EMAIL_PASSWORD=true
ENABLE_MAGIC_LINK_LOGIN=false
```

---

## 3. Configuração do Banco de Dados

### 3.1 Adicionar ao `init-db.sql`

Adicione ao final do seu arquivo `config/init-db.sql`:

```sql
-- =====================================================
-- Script para Plane Database
-- =====================================================

-- Criar database separado para o Plane
CREATE DATABASE plane_db WITH OWNER = rag_user ENCODING = 'UTF8';

-- Conectar ao banco do Plane
\c plane_db

-- Garantir extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- O Plane gerencia suas próprias tabelas via migrations
-- Este script apenas prepara o ambiente

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE plane_db TO rag_user;
GRANT ALL ON SCHEMA public TO rag_user;

-- Schema para separação lógica (opcional)
CREATE SCHEMA IF NOT EXISTS plane;
GRANT ALL ON SCHEMA plane TO rag_user;

-- Retornar ao banco principal
\c ai_rag
```

---

## 4. Deploy e Inicialização

### 4.1 Parar serviços existentes (se necessário)

```bash
docker compose down
```

### 4.2 Rebuild do PostgreSQL com novo init-db.sql

```bash
# Se o PostgreSQL já estava rodando, você precisa recriar o volume ou rodar o SQL manualmente
docker compose up -d postgres
docker compose exec postgres psql -U rag_user -d ai_rag -f /docker-entrypoint-initdb.d/init-db.sql
```

### 4.3 Subir serviços do Plane

```bash
docker compose up -d plane-redis plane-minio
docker compose up -d plane-api
docker compose up -d plane-worker plane-beat-worker
docker compose up -d plane-web
```

### 4.4 Verificar logs

```bash
# Verificar migração do banco
docker compose logs plane-api | grep -i migration

# Verificar saúde dos serviços
docker compose ps | grep plane
```

---

## 5. Acesso e Configuração Inicial

### 5.1 Acessar Interface Web

1. Abra o navegador em: **http://localhost:3002**
2. Crie sua conta de administrador
3. Configure seu primeiro workspace

### 5.2 Gerar API Key

1. Acesse **Settings → API Tokens**
2. Clique em **Create New Token**
3. Dê um nome descritivo: `BMAD-MCP-Integration`
4. Copie o token gerado
5. Adicione ao `.env`:

```bash
PLANE_API_KEY=plane_api_xxxxxxxxxxxxxxxxxxxxxxxx
```

### 5.3 Criar Projeto Inicial

1. No Plane, clique em **New Project**
2. Nome: `AI Automation System`
3. Identifier: `AUTO`
4. Description: `Sistema de automação com agentes BMAD`
5. Anote o `project_id` para uso futuro

---

## 6. Integração com MCP (Model Context Protocol)

### 6.1 Instalar Plane MCP Server

```bash
npm install -g @makeplane/plane-mcp-server
```

### 6.2 Configurar no Claude Code

Adicione ao seu `claude_desktop_config.json` ou arquivo de configuração MCP:

```json
{
  "mcpServers": {
    "plane": {
      "command": "npx",
      "args": ["-y", "@makeplane/plane-mcp-server"],
      "env": {
        "PLANE_API_BASE_URL": "http://localhost:3002",
        "PLANE_API_KEY": "plane_api_xxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

### 6.3 Ferramentas MCP Disponíveis

O Plane MCP Server expõe as seguintes ferramentas:

**Projetos:**
- `get_projects` - Lista todos os projetos
- `create_project` - Cria novo projeto
- `update_project` - Atualiza projeto
- `delete_project` - Remove projeto

**Issues:**
- `get_issues` - Lista issues com filtros
- `get_issue_using_readable_identifier` - Busca por ID (ex: AUTO-123)
- `create_issue` - Cria nova issue
- `update_issue` - Atualiza issue
- `delete_issue` - Remove issue
- `add_issue_comment` - Adiciona comentário

**Módulos (Epics):**
- `create_module` - Cria módulo
- `add_module_issues` - Vincula issues ao módulo

**Ciclos (Sprints):**
- `create_cycle` - Cria sprint
- `add_cycle_issues` - Adiciona issues ao sprint

**Equipe:**
- `list_workspace_members` - Lista membros
- `assign_issue` - Atribui issue

---

## 7. Workflow BMAD + Plane MCP

### 7.1 Fase 1: Planning (Web UI com Gemini 1M tokens)

```
┌─────────────────────────────────────────────┐
│   Analyst Agent → Project Brief             │
│   PM Agent → PRD com User Stories           │
│        ↓                                     │
│   Plane MCP: create_project                 │
│   Plane MCP: create_module (para cada Epic) │
└─────────────────────────────────────────────┘
```

**Exemplo de uso com Claude:**

```
Usando o Plane MCP, crie um novo projeto chamado "AI Automation System" 
com identificador "AUTO" no workspace "ai-automation".

Em seguida, crie um módulo chamado "BMAD-SCRUM Integration" neste projeto.
```

### 7.2 Fase 2: Sprint Planning (Claude Code + Scrum Master Agent)

```
┌─────────────────────────────────────────────┐
│   Scrum Master Agent analisa PRD            │
│        ↓                                     │
│   Para cada User Story:                     │
│     - Plane MCP: create_issue               │
│     - Plane MCP: add_module_issues          │
│        ↓                                     │
│   Plane MCP: create_cycle (Sprint 1)        │
│   Plane MCP: add_cycle_issues (priorizadas) │
└─────────────────────────────────────────────┘
```

**Exemplo Python:**

```python
from plane_mcp import PlaneMCPClient

plane = PlaneMCPClient(
    base_url="http://localhost:3002",
    api_key=os.getenv("PLANE_API_KEY")
)

# Criar sprint
cycle = plane.create_cycle(
    workspace_slug="ai-automation",
    project_id="auto-project-id",
    name="Sprint 1 - Foundation",
    start_date="2025-10-27",
    end_date="2025-11-10"
)

# Criar issues a partir do PRD
for story in prd_stories:
    issue = plane.create_issue(
        workspace_slug="ai-automation",
        project_id="auto-project-id",
        name=story.title,
        description=story.description,
        priority="high"
    )
    
    # Adicionar ao sprint
    plane.add_cycle_issues(
        workspace_slug="ai-automation",
        project_id="auto-project-id",
        cycle_id=cycle.id,
        issues=[issue.id]
    )
```

### 7.3 Fase 3: Development (Developer Agent)

```
┌─────────────────────────────────────────────┐
│   Developer Agent implementa story          │
│        ↓                                     │
│   Ao completar:                             │
│     - Plane MCP: update_issue (Done)        │
│     - Plane MCP: add_issue_comment          │
│       "Implementado em commit abc123"       │
└─────────────────────────────────────────────┘
```

### 7.4 Fase 4: Quality & Reflection

```
┌─────────────────────────────────────────────┐
│   Reflection MCP avalia qualidade           │
│        ↓                                     │
│   Se problemas detectados:                  │
│     - Plane MCP: create_issue (tipo: bug)   │
│     - Plane MCP: assign_issue               │
└─────────────────────────────────────────────┘
```

---

## 8. Automação com n8n

### 8.1 Workflow: Sincronização GitHub ↔ Plane

```
Trigger: GitHub Issue Created
  ↓
HTTP Request: Plane API - Create Issue
  ↓
Set Variable: mapping[github_id] = plane_id
  ↓
Webhook Response: Success
```

### 8.2 Workflow: Daily Standup Automático

```
Schedule: Every day 9:00 AM
  ↓
Plane MCP: get_issues (assigned_to: team, status: in_progress)
  ↓
Format: Markdown summary
  ↓
Send to Slack/Discord
```

---

## 9. Vantagens da Integração

✅ **Reutilização de Infraestrutura**: Usa PostgreSQL existente  
✅ **Automação Total**: Issues criadas automaticamente via PRDs  
✅ **Sincronização Bidirecional**: GitHub ↔ Plane via MCP  
✅ **Visibilidade Completa**: Dashboard unificado  
✅ **Agentic Workflows**: BMAD gerencia sprints automaticamente  
✅ **Self-hosted**: Controle total dos dados  
✅ **Open Source**: Licença AGPL-3.0  

---

## 10. Monitoramento e Troubleshooting

### Acessos
- Plane Web: http://localhost:3002

- MinIO Console: http://localhost:9001

- API Health: http://localhost:3002/api/health/

### 10.1 Verificar Status dos Serviços

```bash
# Status geral
docker compose ps | grep plane

# Logs específicos
docker compose logs -f plane-api
docker compose logs -f plane-worker
```

### 10.2 Acessar PostgreSQL

```bash
# Via Docker
docker compose exec postgres psql -U rag_user -d plane_db

# Listar tabelas do Plane
\dt
```

### 10.3 Acessar MinIO Console

Acesse: **http://localhost:9001**

Credenciais:
- Username: `plane-minio-access`
- Password: (valor de `PLANE_MINIO_ROOT_PASSWORD`)

### 10.4 Problemas Comuns

**Issue: Plane API não sobe**
```bash
# Verificar logs de migração
docker compose logs plane-api | grep -i error

# Verificar conexão com banco
docker compose exec plane-api env | grep DATABASE_URL
```

**Issue: Uploads não funcionam**
```bash
# Verificar MinIO
docker compose exec plane-minio mc admin info local

# Verificar bucket criado
docker compose exec plane-minio mc ls local/plane-uploads
```

---

## 11. Próximos Passos

1. ✅ **Deploy do Plane**: `docker compose up -d plane-web plane-api plane-worker`
2. ✅ **Criar Workspace**: Acessar http://localhost:3002
3. ✅ **Gerar API Key**: Settings → API Tokens
4. ✅ **Configurar MCP**: Adicionar ao Claude Code
5. ✅ **Testar Integração**: Criar primeiro projeto via MCP
6. ✅ **Integrar com BMAD**: Configurar agentes para usar Plane MCP
7. 🔄 **Criar Workflows n8n**: Automação GitHub ↔ Plane
8. 🔄 **Setup Monitoring**: highlight.io + OpenTelemetry

---

## 12. Referências

- [Plane Official Documentation](https://developers.plane.so/self-hosting/methods/docker-compose)
- [Plane MCP Server GitHub](https://github.com/makeplane/plane-mcp-server)
- [BMAD Methodology](../BMAD_METHODOLOGY.md)
- [MCP Ecosystem](../MCP_ECOSYSTEM.md)
- [Database Setup](../DATABASE_SETUP.md)

---

## Apêndice A: Schema do Plane no PostgreSQL

O Plane cria automaticamente as seguintes tabelas principais:

- `plane_workspace` - Workspaces
- `plane_project` - Projetos
- `plane_issue` - Issues/Tarefas
- `plane_module` - Módulos (Epics)
- `plane_cycle` - Ciclos (Sprints)
- `plane_comment` - Comentários
- `plane_user` - Usuários
- `plane_team` - Equipes

**Nota**: Estas tabelas são gerenciadas automaticamente pelas migrations do Plane. Não altere manualmente.

---

## Apêndice B: Comandos Úteis

```bash
# Reiniciar apenas serviços Plane
docker compose restart plane-web plane-api plane-worker plane-beat-worker

# Rebuild completo
docker compose up -d --build plane-api

# Backup do banco do Plane
docker compose exec postgres pg_dump -U rag_user plane_db > backup_plane_$(date +%Y%m%d).sql

# Restore do banco
docker compose exec -T postgres psql -U rag_user plane_db < backup_plane_20251026.sql
```

---

**Versão**: 1.0  
**Última Atualização**: 26 de Outubro de 2025  
**Autor**: AI-Stack Development Team
