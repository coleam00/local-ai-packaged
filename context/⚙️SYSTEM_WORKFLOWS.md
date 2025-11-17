# **⚙️ Guia de Implementação e Workflows do Sistema**

> Status: atualizado para a stack consolidada (start_services.py + Caddy) — inclui Portainer e LiteLLM via proxy local.

## Visão rápida (Runbook em produção)
- Script de orquestração: `start_services.py`
  - Clona/configura Supabase local e copia `.env`
  - Injeta o schema RAG em `supabase/docker/volumes/db/init/02-rag-schema.sql`
  - Sobe Supabase primeiro, aguarda `pg_isready`
  - Gera secret do SearXNG na primeira execução
  - Sobe serviços da stack (perfís: `cpu`, `gpu-nvidia`, `gpu-amd`)
- Reverse proxy: Caddy com hostnames `.env` (ex.: `:8001` n8n, `:8002` WebUI, `:8009` RAG)
- Gerência visual: Portainer via Caddy (`PORTAINER_HOSTNAME`, padrão `:8010`)
- LiteLLM: executa no host em `http://host.docker.internal:4000/v1` (usado pelo Archon e serviços que apontarem `LLM_BASE_URL`).

## Serviços principais (compose atual)
- n8n, Open WebUI, Flowise, RAG (API/ingestion), Redis/Valkey, SearXNG, Langfuse (web/worker + Postgres + ClickHouse + MinIO), Neo4j, Caddy, Portainer.
- Supabase (incluído via include do compose da pasta `supabase/docker/`).

## Ações rápidas
- CPU: `python start_services.py --profile cpu`
- NVIDIA: `python start_services.py --profile gpu-nvidia`
- AMD: `python start_services.py --profile gpu-amd`
- Ingestão one-shot: `docker compose -p localai --profile ingestion up --build rag-ingestion`
- Saúde do RAG: `curl http://localhost:8009/health`
- Portainer: abra `http://localhost:8010` (ou seu domínio em `PORTAINER_HOSTNAME`)

Este documento é um guia prático e técnico para configurar, operar e manter o ecossistema de desenvolvimento assistido por IA.

> **📘 Documentos de Referência:**
> *   **Metodologia:** [`BMAD.md`](📋BMAD.md)
> *   **Arquitetura:** [`архитектура/CONTEXT.md`](../архитектура/CONTEXT.md)

## **1. Configuração do Ambiente**

### **1.1. Variáveis de Ambiente Essenciais (`.env`)**

```bash
# Supabase (para RAG e Auth)
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# PostgreSQL (para Plane)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433 # Porta diferente para evitar conflito com Supabase local
POSTGRES_USER=plane_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=plane_db

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password

# LightRAG Server
LIGHTRAG_PORT=9621

# LiteLLM Proxy
LITELLM_PORT=4000
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx

# Plane API Key (obter da UI do Plane)
PLANE_API_KEY=plane_api_xxx
```

### **1.2. Comandos do Docker Compose**

O `docker-compose.yml` na raiz do projeto orquestra os serviços auto-hospedados (Plane, Neo4j, n8n, etc.).

```bash
# Iniciar todos os serviços em background
docker compose up -d

# Verificar status dos contêineres
docker compose ps

# Ver logs em tempo real (essencial para debug)
docker compose logs -f lightrag neo4j n8n plane-api

# Parar e remover todos os serviços
docker compose down
```

## **2. Workflows de Automação (n8n)**

### **2.1. Pipeline de Ingestão de Documentos para RAG**

Este workflow automatiza a atualização da nossa base de conhecimento.

*   **Gatilho:** Webhook do Git (disparado a cada `push` para a branch `main`).
*   **Passos:**
    1.  **Clonar Repositório:** Clona a versão mais recente do projeto.
    2.  **Identificar Mudanças:** Lista os arquivos Markdown modificados na pasta `/memory-bank`.
    3.  **Loop por Arquivo:**
        a. **Calcular Hash:** Gera um hash SHA-256 do conteúdo do arquivo.
        b. **Verificar Duplicidade:** Consulta o Supabase para ver se o hash já existe. Se sim, pula.
        c. **Chamar LightRAG API:** Envia o arquivo para o endpoint `/documents/file` do LightRAG, que orquestra o sharding, embedding e a persistência no Supabase e Neo4j.

### **2.2. Sincronização GitHub ↔ Plane**

Este workflow mantém nosso gerenciamento de projetos e o desenvolvimento alinhados.

*   **Gatilho:** Webhook do GitHub (eventos de `issues`, `pull_request`).
*   **Lógica:**
    *   **Nova Issue no GitHub:** Cria uma issue correspondente no Plane com um link para a issue original.
    *   **Novo Pull Request no GitHub:** Cria uma issue no Plane, a associa ao épico correto e a move para a coluna "Em Revisão".
    *   **Comentário no Plane:** Pode postar atualizações de status de volta para a issue do GitHub.

### **Expansão: 2.3 Automação GitHub Avançada com CLI e Copilot**

#### **2.3.1 Pipeline n8n para Sincronização GitHub ↔ Plane com MCP**

**Novo Workflow Completo:**

```yaml
# workflows/n8n/github-plane-sync.json
{
  "name": "GitHub-Plane Bidirectional Sync",
  "nodes": [
    {
      "id": "github_webhook_trigger",
      "type": "Webhook",
      "config": {
        "path": "github-sync",
        "method": "POST",
        "auth": "GitHub App Signature Verification"
      }
    },
    {
      "id": "parse_github_event",
      "type": "Function",
      "code": `
        const event = $input.body;
        if (event.action === 'opened' && event.issue) {
          return { type: 'issue_opened', issue: event.issue };
        } else if (event.action === 'opened' && event.pull_request) {
          return { type: 'pr_opened', pr: event.pull_request };
        }
        return { type: 'ignored' };
      `
    },
    {
      "id": "analyze_with_mcp",
      "type": "MCP Server",
      "config": {
        "server": "github-mcp",
        "tool": "analyze_issue",
        "params": {
          "issue_body": "{{ $node.parse_github_event.json.issue.body }}",
          "issue_title": "{{ $node.parse_github_event.json.issue.title }}"
        }
      }
    },
    {
      "id": "create_plane_task",
      "type": "HTTP Request",
      "config": {
        "method": "POST",
        "url": "{{ env.PLANE_API_BASE }}/workspaces/{{ env.PLANE_WORKSPACE }}/projects/{{ env.PLANE_PROJECT }}/issues/",
        "headers": {
          "Authorization": "Bearer {{ env.PLANE_API_KEY }}",
          "Content-Type": "application/json"
        },
        "body": {
          "name": "{{ $node.parse_github_event.json.issue.title }}",
          "description": "{{ $node.analyze_with_mcp.json.analysis }}\n\n**GitHub Link:** {{ $node.parse_github_event.json.issue.html_url }}",
          "priority": "{{ mapPriority($node.analyze_with_mcp.json.priority) }}",
          "estimate": "{{ $node.analyze_with_mcp.json.estimate_points }}",
          "labels": ["auto-synced-from-github", "{{ $node.parse_github_event.json.issue.labels[0].name }}"]
        }
      }
    },
    {
      "id": "update_github_issue",
      "type": "GitHub API",
      "config": {
        "action": "addComment",
        "owner": "{{ owner }}",
        "repo": "{{ repo }}",
        "issue_number": "{{ $node.parse_github_event.json.issue.number }}",
        "body": "✅ Tarefa criada no Plane: [{{ $node.create_plane_task.json.id }}]({{ planeLinkForIssue($node.create_plane_task.json.id) }})"
      }
    },
    {
      "id": "notify_slack",
      "type": "Slack",
      "config": {
        "channel": "#development",
        "message": "🔄 Sincronizado: GitHub Issue → Plane Task\n• **Issue:** {{ $node.parse_github_event.json.issue.title }}\n• **Plane ID:** {{ $node.create_plane_task.json.id }}\n• **Prioridade:** {{ $node.analyze_with_mcp.json.priority }}"
      }
    }
  ]
}
```

---

#### **2.3.2 Instalação do Copilot CLI como Serviço Docker**

O Copilot CLI pode ser rodado como agente persistente em Docker para automação contínua.

```dockerfile
# Dockerfile.copilot-cli
FROM node:22-alpine

# Instalar Copilot CLI
RUN npm install -g @github/copilot

# Setup de usuário não-root
RUN adduser -D copilot
WORKDIR /workspace
USER copilot

# Entrypoint que mantém Copilot rodando em modo watch
ENTRYPOINT ["copilot", "watch"]
```

```yaml
# docker-compose.yml (adição)
services:
  copilot-cli-agent:
    build:
      context: .
      dockerfile: Dockerfile.copilot-cli
    environment:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
      COPILOT_MODEL: "claude-sonnet"  # ou gpt-5 quando disponível
      MCP_CONFIG: "/config/mcp.json"
    volumes:
      - ./workspace:/workspace
      - ./config/mcp.json:/config/mcp.json
    networks:
      - ai-stack
    healthcheck:
      test: ["CMD", "copilot", "--version"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Configuração de MCP Customizados para Copilot CLI:**

```json
{
  "mcp_servers": {
    "github": {
      "command": "node",
      "args": ["mcp-server-github/dist/index.js"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "plane": {
      "command": "node",
      "args": ["mcp-server-plane/dist/index.js"],
      "env": {
        "PLANE_API_KEY": "${PLANE_API_KEY}",
        "PLANE_BASE_URL": "http://plane:3000"
      }
    },
    "lightrag": {
      "command": "python",
      "args": ["mcp-server-lightrag/server.py"],
      "env": {
        "LIGHTRAG_API": "http://lightrag:9621"
      }
    }
  }
}
```

---

#### **2.3.3 GitHub Actions Workflow Otimizado com Agent HQ**

```yaml
# .github/workflows/agentic-development.yml
name: Agentic Development Workflow

on:
  issue_comment:
    types: [created]
  issues:
    types: [labeled]
  pull_request:
    types: [opened, synchronize]

jobs:
  agent-orchestration:
    name: Multi-Agent Orchestration
    runs-on: ubuntu-latest
    
    permissions:
      contents: write
      issues: write
      pull-requests: write
    
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code

      - name: Install GitHub Copilot CLI
        run: npm install -g @github/copilot

      - name: Load Mission Control Config
        id: mission-control
        run: |
          echo "MISSION_CONFIG=$(cat .github/mission-control.yml)" >> $GITHUB_OUTPUT

      - name: Run Agentic Workflow
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PLANE_API_KEY: ${{ secrets.PLANE_API_KEY }}
        run: |
          # Paralleliza agentes conforme Mission Control config
          copilot "Execute mission control: ${{ steps.mission-control.outputs.MISSION_CONFIG }}" \
            --mcp-config .github/mcp-config.json \
            --async
          
          # Aguarda conclusão com timeout
          timeout 3600 bash -c 'until [ -f /tmp/mission-complete.flag ]; do sleep 10; done'

      - name: Generate Report
        if: always()
        run: |
          # Coleta logs de todos os agentes
          cat .agent/reports/*.md > MISSION_REPORT.md
          echo "## Mission Status" >> MISSION_REPORT.md
          cat /tmp/mission-status.json >> MISSION_REPORT.md

      - name: Post Report to PR
        uses: actions/github-script@v7
        if: github.event_name == 'pull_request'
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('MISSION_REPORT.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```



## **3. Integração com Claude Code**

### **3.1. Configuração Essencial (`.claude/settings.local.json`)**

```json
{
  "autoconnect": true,
  "hooks": [
    {
      "event": "PostToolUse",
      "command": "npm run lint:fix",
      "description": "Formata o código automaticamente após cada alteração."
    },
    {
      "event": "PostToolUse",
      "command": "npm run test:related",
      "description": "Executa testes relacionados ao arquivo modificado."
    }
  ],
  "mcpServers": {
    "plane": {
      "command": "npx",
      "args": ["-y", "@makeplane/plane-mcp-server"],
      "env": {
        "PLANE_API_BASE_URL": "http://localhost:3002",
        "PLANE_API_KEY": "${PLANE_API_KEY}"
      }
    }
  }
}
```

### **3.2. Comandos Slash Personalizados (`.claude/commands/`)**

Criar comandos personalizados acelera workflows repetitivos.

**Exemplo: `.claude/commands/new_feature.md`**
```markdown
---
name: new_feature
description: Inicia o workflow completo de planejamento para uma nova feature.
arguments:
  - name: featureName
    description: O nome da feature a ser planejada.
---
# Iniciar Planejamento para a Feature: {{featureName}}

1.  **Brainstorm:** Execute uma análise de mercado e de concorrentes para a feature "{{featureName}}".
2.  **Criar Brief:** Crie um `Project Brief` inicial e salve em `/memory-bank/briefs/{{featureName}}.md`.
3.  **Criar Épico no Plane:** Use a ferramenta `plane.create_module` para criar um novo épico no projeto atual com o nome "{{featureName}}".
```

### **3.3. Desenvolvimento Paralelo com Git Worktrees**

Para explorar diferentes abordagens para uma mesma tarefa complexa.

```bash
# 1. Preparar ambientes paralelos para a feature 'auth-flow'
/prep-parallel feature-auth-flow 3

# 2. Executar o desenvolvimento em 3 worktrees diferentes, cada um com uma abordagem
/execute-parallel feature-auth-flow "Implemente o fluxo de autenticação" 3

# 3. Listar os worktrees e revisar os resultados
git worktree list
# Escolha a melhor implementação e faça o merge
git merge feature-auth-flow-2
```

## **4. Operações e Manutenção**

### **4.1. Backup Automatizado**

Um script `backup.sh` agendado via cron job para fazer backup dos dados críticos.

```bash
# filepath: scripts/backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# 1. Banco de Dados do Plane (PostgreSQL)
docker compose exec postgres pg_dump -U plane_user -d plane_db | gzip > ${BACKUP_DIR}/plane_db_${DATE}.sql.gz

# 2. Grafo (Neo4j)
docker exec neo4j neo4j-admin database dump neo4j --to-path=/backups/neo4j_${DATE}.dump

# 3. Memory Bank (Arquivos Git) - O próprio Git já é um backup, mas um tarball pode ser útil
git archive --format=tar.gz -o ${BACKUP_DIR}/memory_bank_${DATE}.tar.gz main

echo "✅ Backup concluído em ${BACKUP_DIR}"
```

### **4.2. Troubleshooting Comum**

| Problema | Diagnóstico | Solução |
| :--- | :--- | :--- |
| **Respostas RAG ruins** | Verifique os logs do LightRAG. A consulta está chegando? O contexto recuperado faz sentido? | Re-ingerir os documentos. Verificar se o n8n está processando corretamente. Ajustar o modelo de embedding ou as estratégias de sharding. |
| **Plane não inicia** | `docker compose logs plane-api` | Verificar se as variáveis de ambiente do PostgreSQL estão corretas e se a porta não está em conflito. |
| **Claude não conecta** | Verifique a saída do terminal do Claude Code. | Execute `/id` manualmente. Verifique se a extensão do VS Code/Cursor está instalada e ativa. |