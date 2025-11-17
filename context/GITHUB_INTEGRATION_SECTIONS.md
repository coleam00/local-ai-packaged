# 🚀 Complementações Modulares: Integração GitHub, Copilot CLI e Automação Agentic

---

## **📋 SEÇÃO 1: CLAUDE_CODE_GUIDE.md**
### **Expansão: 5. Automação do Ciclo de Vida com Integração GitHub (Revisada e Ampliada)**

#### **5.1 Instalação Nativa: Comando `/install-github-app`**

O comando `/install-github-app` é o ponto de entrada automatizado para integração Claude Code ↔ GitHub. Diferente de configurações manuais, este comando orquestra todo o fluxo de autorização, permissões e secrets.

```bash
# Dentro do Claude Code, executar:
/install-github-app
```

**Fluxo Automatizado:**
1. **Detecção Local:** Claude Code identifica se você está dentro de um repositório Git
2. **Seleção de Repositório:** Oferece opção de selecionar o repositório ou usar um diferente
3. **Abertura do Navegador:** Redireciona para GitHub para instalação do app "Claude"
4. **Autorização de Permissões:** O app solicita:
   - **Contents:** Leitura e escrita para modificar arquivos
   - **Issues:** Leitura e escrita para responder issues
   - **Pull Requests:** Leitura e escrita para criar/atualizar PRs
5. **Adição de Secrets:** Após aprovação, adiciona `ANTHROPIC_API_KEY` aos GitHub Secrets automaticamente
6. **Validação:** Claude Code confirma a conexão testando um commit simples

**Benefício Crítico:** Este fluxo elimina 90% do atrito manual, tornando a integração um processo único, sem necessidade de conhecimento técnico prévio sobre GitHub Actions ou secrets management.

---

#### **5.2 GitHub Copilot CLI: O Novo Agente Terminal (Public Preview - Setembro 2025)**

O **GitHub Copilot CLI** substitui completamente a extensão `gh-copilot` (deprecada em outubro/2025) e introduz uma arquitetura agentic verdadeira na linha de comando.

**Instalação:**
```bash
npm install -g @github/copilot
copilot auth login  # Autenticação com GitHub
```

**Capacidades Agentic Nativas:**

| Capacidade | Descrição | Caso de Uso |
|-----------|-----------|-----------|
| **Planejamento Multi-Passo** | Decomposição automática de tarefas complexas | Implementar feature com múltiplas dependências |
| **Execução com Controle** | Preview de alterações antes de aplicar | Revisão de segurança integrada |
| **Integração MCP Nativa** | GitHub MCP server incluso; suporta custom MCPs | Extensibilidade sem limites |
| **Sincronização GitHub Automática** | Acesso ao contexto de issues, PRs, branches | Referência direta a issues na conversa |
| **Modo Chat + Modo Agentic** | Seleção entre interação conversacional ou autônoma | Flexibilidade conforme contexto |

**Fluxo de Uso Prático:**
```bash
# Modo chat interativo (com preview)
copilot

# Modo específico: explorar repositório
copilot "Como funciona a autenticação neste projeto?"

# Modo específico: implementar tarefa
copilot "Implemente o fluxo de logout mencionado na issue #42"

# Com MCP customizado
copilot --mcp-config ~/.copilot/custom-mcps.json "Liste todos os TODOs deste projeto"
```

**Diferença Crítica: Copilot CLI vs gh-copilot**

| Aspecto | `gh-copilot` (Descontinuado) | **Copilot CLI** (Novo) |
|--------|------------|-----------|
| **Modelo Arquitetural** | Gerador de sugestões simples | Agente agentic completo |
| **Autonomia** | Apenas sugere comandos | Planeja e executa tarefas |
| **MCP Support** | Não | ✅ MCP out-of-box + custom |
| **GitHub Context** | Limitado | Profundo (issues, PRs, branches) |
| **Billing** | Separado | Integrado ao Copilot Pro/Business |
| **Deprecação** | Outubro 25, 2025 | ✅ Ativo e evoluindo |

---

#### **5.3 Gatilhos Automatizados: GitHub ↔ Plane ↔ n8n ↔ Claude Code**

A integração bidirecional cria um loop de automação onde cada evento dispara agentes especializados.

**Arquitetura de Fluxo:**
```
Issue criada no GitHub
    ↓
[n8n Webhook] → Analisa issue com MCP
    ↓
Cria task no Plane (com link para issue)
    ↓
[Claude Code] → Pick up task, implementa
    ↓
Abre PR com commit automático
    ↓
[GitHub] → Comenta PR com status Plane
    ↓
[Humano] → Revisa, comenta
    ↓
[Claude Code] → Incorpora feedback, faz merge
```

**Configuração do Webhook n8n:**

```json
{
  "name": "GitHub Issue → Plane Task",
  "trigger": "Webhook (GitHub events: issues, pull_request)",
  "nodes": [
    {
      "type": "GitHub Node",
      "action": "getIssue",
      "filter": "state === 'open' && labels.includes('ready-for-dev')"
    },
    {
      "type": "MCP Call",
      "server": "github-mcp",
      "action": "analyze_issue",
      "prompt": "Extrair requisitos técnicos e estimar esforço"
    },
    {
      "type": "Plane API",
      "action": "create_issue",
      "mapping": {
        "title": "{{ github.issue.title }}",
        "description": "{{ mcp_analysis.requirements }}",
        "estimate": "{{ mcp_analysis.effort_points }}",
        "github_url": "{{ github.issue.html_url }}"
      }
    },
    {
      "type": "Slack Notification",
      "message": "✅ Nova tarefa no Plane: {{ plane.issue.id }}"
    }
  ]
}
```

**Hooks Pós-Execução (Claude Code):**

Após cada implementação, triggers automáticos executam validações:

```json
{
  "hooks": [
    {
      "event": "PostFileWrite",
      "command": "npm run lint:fix -- {{file}}",
      "description": "Formata automaticamente após edição"
    },
    {
      "event": "PostFileWrite",
      "command": "npm run type-check",
      "description": "Valida tipos TypeScript em tempo real"
    },
    {
      "event": "PreCommit",
      "command": "npm run test:related -- {{files}}",
      "description": "Executa testes relacionados antes do commit"
    },
    {
      "event": "PostCommit",
      "command": "curl -X POST https://n8n.instance/webhook/post-commit -d '{{commit_data}}'",
      "description": "Notifica n8n de novo commit para síntese de changelog"
    }
  ]
}
```

---

#### **5.4 Arquivo `AGENTS.md`: Registro Formal de Agentes e Governança**

O arquivo `AGENTS.md` centraliza a definição de todos os agentes operacionais, suas responsabilidades, limites e como interagem.

**Estrutura Padrão:**

```markdown
# 🤖 AGENTS.md - Registro de Agentes Operacionais

## 1. Agente: Claude Code (Desenvolvedor Principal)

**Endpoint:** Terminal Claude Code
**Modelos:** Claude Sonnet 4.5, Opus (conforme complexity)
**Funções:**
- Implementação de features de alto nível
- Refatoração de código
- Escrita de testes
- Revisão de PRs (análise automática)

**Restrições:**
- Não pode fazer deploy sem aprovação humana
- Não pode modificar secrets ou configurações críticas
- Máximo 5 PRs simultâneas

**Contexto Obrigatório:**
- `claude.md` (projeto específico)
- `ARCHITECTURE.md` (referência)
- `agents.md` (este arquivo)

**Integração:**
- GitHub App instalado via `/install-github-app`
- MCP Plane para acesso a tarefas
- Webhooks n8n para sincronização

---

## 2. Agente: GitHub Copilot CLI (Terminal Agent)

**Endpoint:** `copilot` CLI command
**Modelos:** Claude Sonnet 4.5 (default), alternáveis via `COPILOT_MODEL`
**Funções:**
- Exploração de codebase
- Análise de issues
- Geração de planos de implementação
- Debugging colaborativo

**Restrições:**
- Todas as ações requerem preview + aprovação explícita
- Sem acesso a repositórios privados sem authenticação
- Rate-limited pelo GitHub Copilot Pro subscription

**Contexto Disponível:**
- GitHub issues nativas
- PRs na branch
- Histórico de commits

**Integração:**
- MCP servers customizados (`--mcp-config`)
- Plane via MCP server próprio
- n8n webhooks para acionamento externo

---

## 3. Agente: n8n Workflow Orchestrator

**Endpoint:** n8n Web UI + Webhooks
**Modelos:** LiteLLM Proxy (múltiplos modelos via configuração)
**Funções:**
- Orquestração de eventos GitHub ↔ Plane
- Ingestão de documentos RAG
- Sincronização de status bidirecional
- Notificações e alertas

**Restrições:**
- Executa apenas workflows aprovados no repositório
- Logs de auditoria de todas as ações
- Timeout de 10 minutos por workflow

**Contexto Recebido:**
- Payload de webhooks GitHub
- Dados de tarefas Plane via API
- Documentos RAG via LightRAG

**Integração:**
- GitHub webhooks
- Plane API (autenticação via token seguro)
- n8n MCP server para orchestração

---

## 4. Agente: LiteLLM Router (Gateway Centralizado)

**Endpoint:** `http://litellm-proxy:4000`
**Modelos:** 100+ modelos suportados (Claude, GPT-4, Gemini, etc.)
**Funções:**
- Abstração unificada de LLMs
- Roteamento inteligente por custo/latência
- Cache de respostas
- Logging de uso e custo

**Restrições:**
- Suporta fallback automático (modelo A → modelo B)
- Rate limit: 1000 req/min por organização
- Timeout: 60s por request

**Configuração de Modelo:**
```yaml
model_list:
  - model_name: "primary-generation"
    litellm_params:
      model: "claude/claude-3-5-sonnet"
  - model_name: "fallback-generation"
    litellm_params:
      model: "gpt-4-turbo"
```

**Integração:**
- LightRAG para queries RAG
- Claude Code para fallback de modelos
- Copilot CLI para alternância dinâmica

---

## 5. Matrix de Comunicação Inter-Agentes

```
Claude Code ←→ GitHub Copilot CLI
    ↓                  ↓
    ├→ n8n ←→ Plane ←→ GitHub
    ├→ LightRAG (RAG)
    ├→ LiteLLM (Model Selection)
    └→ MCP Servers (Plane, GitHub)
```

---

## 6. Governança e Auditoria

**Quando um agente interage com crítico (deploy, deletar):**
1. Requer aprovação explícita human-in-the-loop
2. Registra em `audit.log` com timestamp + contexto completo
3. Notifica via Slack/webhook designado
4. Revertível dentro de 1 hora (git revert automático)

**Escalation Automática:**
- Se agente encontra erro 3x seguidas → humano recebe alert
- Se agente supera budget de tokens → interrupção automática + resumo
- Se taxa de falha > 20% → desativa workflow até revisão

---

## 7. Onboarding de Novo Agente

Para registrar novo agente (ex: Gemini CLI):

1. Criar seção neste arquivo seguindo template acima
2. Definir permissões no `.github/workflows/agent-permissions.yml`
3. Registrar modelo no `config/model-routing.yaml`
4. Validar integração em ambiente de staging
5. Merge após aprovação de 2 senior engineers

```bash
# Verificar conformidade
/validate-agent-config NEW_AGENT_NAME
```
```

---

#### **5.5 Power Prompts: Templates de Automação Reutilizável**

Power Prompts são arquivos `.md` salvos em `.claude/power-prompts/` que encapsulam lógica complexa para reutilização por toda equipe.

**Estrutura de Power Prompt:**

```markdown
---
name: "Refactor to Async Awaited"
category: "code-quality"
tags: ["async", "performance", "refactoring"]
version: "1.0"
author: "senior-engineer"
---

# Power Prompt: Refactor Callback Hell to Async/Await

## Context
This prompt transforms callback-based async code into modern async/await patterns, following our architectural standards.

## Prerequisites
- TypeScript 4.5+
- Node 16+
- All existing tests passing

## Execution Steps

### Step 1: Analysis Phase
Analyze the following code for callback patterns:
\`\`\`
$SELECTED_FILE
\`\`\`

Identify:
- All callback functions
- Promise chains
- Error handling patterns
- Dependencies on timing

### Step 2: Planning Phase
Create a refactoring plan that:
1. Maintains all existing behavior
2. Preserves error handling semantics
3. Follows our async conventions in `ARCHITECTURE.md`
4. Adds explicit type annotations

### Step 3: Implementation
- Refactor identified patterns
- Add JSDoc comments for new signatures
- Update related test files

### Step 4: Validation
- Run full test suite
- Check for performance regressions
- Validate TypeScript strict mode

## Safety Gates
- Reject refactoring if tests fail
- Validate async/await patterns against linter config
- Require human approval for behavioral changes
```

**Biblioteca de Power Prompts Críticos:**

| Nome | Categoria | Propósito | Time Beneficiada |
|------|-----------|----------|-----------------|
| `code-review-security` | Security | Audit de segurança em PRs | DevSecOps |
| `generate-changelog` | Docs | Extrai mudanças semânticas de commits | Release Mgmt |
| `test-coverage-analysis` | QA | Identifica gaps de cobertura de testes | QA Engineers |
| `dependency-audit` | DevOps | Escaneia vulnerabilidades de dependências | DevOps |
| `performance-profiling` | Performance | Analisa gargalos e sugere otimizações | Backend Team |
| `refactor-monolith-to-microservice` | Architecture | Guia decomposição de sistemas grandes | Architects |

**Como Executar Power Prompt:**
```bash
/power-prompt "code-review-security" --file src/auth.ts --severity high
```

---

#### **5.6 Desenvolvimento Paralelo com Copilot CLI + Agent HQ**

O novo **GitHub Agent HQ** com **Mission Control** permite orquestração de múltiplos agentes simultâneos.

**Setup de Mission Control:**

```yaml
# .github/mission-control.yml
mission:
  name: "Feature: User Authentication Refactor"
  priority: "high"
  deadline: "2025-11-15"
  
agents:
  - id: "claude-code-analyzer"
    role: "Analyzer"
    task: "Map current auth architecture"
    model: "claude-opus"
    constraints:
      - "No code changes, only analysis"
      - "Generate report in .agent/analysis.md"
  
  - id: "copilot-cli-planner"
    role: "Planner"
    task: "Create step-by-step refactoring plan"
    model: "claude-sonnet"
    depends_on: "claude-code-analyzer"
    constraints:
      - "Review analysis output before planning"
  
  - id: "claude-code-implementer"
    role: "Implementer"
    task: "Execute refactoring plan"
    model: "claude-opus"
    depends_on: "copilot-cli-planner"
    constraints:
      - "Follow plan exactly"
      - "Max 5 commits per hour"

  - id: "copilot-cli-reviewer"
    role: "Reviewer"
    task: "Review PR and suggest improvements"
    model: "claude-sonnet"
    depends_on: "claude-code-implementer"
    constraints:
      - "Generate review comment on PR"

status_tracking:
  sync_interval: "5m"
  notification: "slack"
  dashboard: "true"
```

**Parallelização Inteligente:**
- Agentes em paralelo (analyzer + planner simultâneos onde possível)
- Dependency management automático
- Failover se um agente falhar
- Human-in-the-loop em decision points críticos

---

## **🔧 SEÇÃO 2: SYSTEM_WORKFLOWS.md**
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

---

## **🧠 SEÇÃO 3: LLM_INTEGRATION.md**
### **Expansão: Copilot CLI como Provider no LiteLLM Proxy**

#### **3.1 Integração do GitHub Copilot CLI no Roteamento LiteLLM**

```yaml
# config/litellm-proxy-config.yaml

model_list:
  # Copilot CLI (GitHub Models)
  - model_name: "github-copilot-sonnet"
    litellm_params:
      model: "github/claude-3-5-sonnet"
      api_base: "http://copilot-cli-agent:3000"
      api_key: "{{ env.COPILOT_API_TOKEN }}"
  
  - model_name: "github-copilot-opus"
    litellm_params:
      model: "github/claude-opus"
      api_base: "http://copilot-cli-agent:3000"
      api_key: "{{ env.COPILOT_API_TOKEN }}"

  # Fallback ao OpenAI via Copilot CLI
  - model_name: "github-gpt5"
    litellm_params:
      model: "github/gpt-5"
      api_base: "http://copilot-cli-agent:3000"
      api_key: "{{ env.COPILOT_API_TOKEN }}"

# Roteamento estratégico por custo/performance
router_strategy:
  - model: "github-copilot-sonnet"
    priority: 1
    use_case: "general-tasks"
    cost: "low"
  
  - model: "github-copilot-opus"
    priority: 1
    use_case: "complex-reasoning"
    cost: "medium"
  
  - model: "claude-opus-via-anthropic"
    priority: 2
    use_case: "fallback"
    cost: "high"

# Cache de respostas do Copilot CLI
cache_config:
  type: "redis"
  ttl: 3600
  prefix: "copilot-cli"
```

#### **3.2 Dynamic Model Selection via Copilot CLI**

```python
# src/llm_gateway/copilot_router.py

class CopilotModelRouter:
    """
    Roteia requisições dinamicamente entre Copilot CLI e provedores de fallback
    """
    
    def __init__(self, copilot_base_url: str, litellm_proxy: str):
        self.copilot_base = copilot_base_url
        self.litellm = litellm_proxy
        self.cache = RedisCache()
    
    async def route_request(self, query: str, context: Dict) -> Response:
        """
        Route request to best available model based on:
        - Complexity da query
        - Rate limits atuais
        - Custo do modelo
        - Latência esperada
        """
        complexity = self._estimate_complexity(query, context)
        
        if complexity > 0.8:
            # Tarefas complexas → Opus
            model = "github-copilot-opus"
        elif complexity > 0.5:
            # Tarefas médias → Sonnet (default)
            model = "github-copilot-sonnet"
        else:
            # Tarefas simples → Menor custo
            model = "github-copilot-sonnet"
        
        try:
            # Tenta Copilot CLI primeiro
            response = await self._call_copilot_cli(model, query, context)
            
            # Cache para futuras requisições similares
            await self.cache.set(
                key=f"copilot:{hash(query)}",
                value=response,
                ttl=3600
            )
            
            return response
        
        except CopilotRateLimitError as e:
            logger.warning(f"Copilot rate limited, usando fallback: {e}")
            # Fallback automático para OpenAI via LiteLLM
            return await self._call_litellm_fallback("gpt-4", query, context)
        
        except CopilotUnavailableError:
            logger.error("Copilot CLI unavailable, using fallback")
            return await self._call_litellm_fallback("claude-opus", query, context)
    
    async def _call_copilot_cli(self, model: str, query: str, context: Dict):
        """Comunica diretamente com Copilot CLI via MCP"""
        mcp_request = {
            "tool": "generate",
            "model": model,
            "prompt": query,
            "context": context,
            "temperature": 0.7,
            "max_tokens": 4096
        }
        return await self._mcp_call("copilot", mcp_request)
    
    async def _call_litellm_fallback(self, model: str, query: str, context: Dict):
        """Fallback para LiteLLM Proxy quando Copilot não está disponível"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.litellm}/v1/completions",
                json={
                    "model": model,
                    "messages": self._format_messages(query, context),
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
            )
        return response.json()
```

---

## **🔧 SEÇÃO 4: ARCHITECTURE.md**
### **Expansão: Integração Copilot CLI + Agent HQ na Camada de Agentes**

#### **4.1 Novo Diagrama Arquitetural: Multi-Agent Orchestration**

```mermaid
graph TB
    subgraph "Camada de Clientes & Terminais"
        A["🖥️ Claude Code<br/>(Local Dev)"]
        B["⌨️ GitHub Copilot CLI<br/>(Terminal Agent)"]
        C["🌐 OpenWebUI<br/>(Web Interface)"]
    end
    
    subgraph "Camada de Orquestração & Agência (NOVO)"
        D["🎛️ Mission Control<br/>(Agent HQ)"]
        E["🔀 Agent Router<br/>(LiteLLM Enhanced)"]
        F["📋 n8n Orchestrator<br/>(GitHub ↔ Plane)"]
    end
    
    subgraph "Camada MCP & Ferramentas"
        G["🔗 FastMCP Server"]
        H["🔗 GitHub MCP Server"]
        I["🔗 Plane MCP Server"]
        J["🔗 Custom MCP Servers"]
    end
    
    subgraph "Camada de Recuperação & Síntese"
        K["🧠 LightRAG Server<br/>(RAG Hybrid)"]
        L["🎯 LiteLLM Proxy<br/>(Model Gateway)"]
    end
    
    subgraph "Camada de Persistência"
        M["🗄️ PostgreSQL<br/>(Vectors + pgvector)"]
        N["📊 Neo4j<br/>(Knowledge Graphs)"]
    end
    
    A -->|MCP Calls| G
    B -->|MCP Calls| H
    C -->|REST| K
    
    D -->|Route Tasks| E
    E -->|Selects Model| L
    F -->|Webhook Events| D
    
    G ←→ E
    H ←→ D
    I ←→ F
    J ←→ E
    
    K ←→ M
    K ←→ N
    L ←→ M
    
    style D fill:#ffeb3b,stroke:#333,stroke-width:3px,color:#000
    style B fill:#00bcd4,stroke:#333,stroke-width:3px,color:#fff
    style E fill:#ff9800,stroke:#333,stroke-width:3px,color:#fff
```

#### **4.2 Governança de Segurança: Camada Agent HQ**

```yaml
# .github/agent-security-policy.yml

agent_security_framework:
  
  authentication:
    - github_app_verification: true
    - mcp_server_validation: true
    - rate_limiting: "1000 req/min per agent"
  
  authorization:
    - branch_restrictions:
        main: "only-approved-agents"
        develop: "all-agents"
        feature/*: "all-agents"
    
    - file_restrictions:
        - pattern: "src/security/**"
          allowed_agents: ["senior-developer-agent"]
          requires_approval: true
        - pattern: "config/secrets/**"
          allowed_agents: []
          requires_approval: true
    
    - action_restrictions:
        deploy:
          allowed_agents: ["deployment-agent"]
          requires_approval: true
          approval_type: "human-only"
        
        delete_database:
          allowed_agents: []
          requires_approval: true
          approval_type: "2-factor-human"

  audit_logging:
    enabled: true
    destination: "cloudwatch"
    retention: "90 days"
    events:
      - "agent_execution_start"
      - "agent_execution_end"
      - "file_modification"
      - "approval_request"
      - "security_incident"

  incident_response:
    auto_rollback: true
    rollback_window: "1 hour"
    notification_channels: ["slack", "email", "pagerduty"]
    escalation_threshold:
      failure_rate: "20%"
      error_type: "security"
```

---

## **🔌 SEÇÃO 5: MCP_ECOSYSTEM.md**
### **Expansão: GitHub Copilot CLI como MCP Provider Nativo**

#### **5.1 Registro do Copilot CLI MCP Server**

```markdown
### GitHub Copilot CLI MCP Server

**Status:** ✅ Production Ready (v1.0, Sept 2025)
**Tipo:** Terminal-native agentic client
**Modelos Suportados:** Claude Sonnet 4.5, GPT-5, custom via configuration
**Autenticação:** GitHub OAuth via `copilot auth login`

#### Capacidades MCP

| Tool | Descrição | Modo | Retorno |
|------|-----------|------|---------|
| `analyze_code` | Analisa qualidade, segurança, performance | Read-only | JSON report |
| `explore_repo` | Mapeia estrutura, dependências, relacionamentos | Read-only | Graph structure |
| `plan_implementation` | Cria plano multi-step para tarefa | Read-only | Markdown plan |
| `implement_task` | Executa implementação com preview | Read + Write | Code + report |
| `debug_error` | Investiga e propõe fix para erro | Read + Write | Debug report |
| `review_code` | Revisa PR com feedback estruturado | Read-only | Review comment |

#### Configuração no MCP

```yaml
mcp_servers:
  github_copilot_cli:
    command: "copilot"
    args: ["mcp"]
    environment:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
      COPILOT_MODEL: "claude-sonnet"
    capabilities:
      - code_analysis
      - repository_exploration
      - implementation
      - review
      - debugging
    rate_limits:
      requests_per_minute: 60
      tokens_per_hour: 1000000
```

#### Fluxo de Integração

```
User Request
    ↓
Claude Code ←→ Copilot CLI MCP Server
    ↓
Copilot CLI (Terminal)
    ↓
GitHub Context (Issues, PRs, Commits)
    ↓
Response via MCP ← Claude Code
```
```

---

## **📋 SEÇÃO 6: BMAD.md**
### **Integração: Ciclo BMAD com Automação GitHub + Agent HQ**

#### **Novo Segmento: 2.2 Fase 2 Expandida - Automação Agentic**

```markdown
### **Fase 2 Expandida: Desenvolvimento Iterativo com Multi-Agent Orchestration**

Com o lançamento do GitHub Agent HQ e Copilot CLI, o ciclo de desenvolvimento BMAD incorpora orquestração nativa de múltiplos agentes paralelos:

#### **2.2.1 Seleção Estratégica de Agentes por Tarefa**

```
Épico (Plane)
    ↓
Mission Control (Agent HQ)
    ├→ [Analyzer Agent: Claude Code]
    │   └→ Mapeia requisitos + dependências
    │
    ├→ [Planner Agent: Copilot CLI]
    │   └→ Cria plano detalhado (paralelo com Analyzer)
    │
    ├→ [Implementer Agent: Claude Code]
    │   └→ Executa conforme plano
    │
    └→ [Reviewer Agent: Copilot CLI]
        └→ Valida qualidade + alinhamento
```

#### **2.2.2 Sincronização Automática Plane ↔ GitHub ↔ n8n**

O ciclo BMAD agora inclui gatilhos automáticos que mantêm todas as plataformas sincronizadas:

1. **Issue Criada no Plane** →
2. **n8n Webhook** analisa com MCP →
3. **GitHub Issue Criada** (link bidirecional) →
4. **Claude Code Detecta** via `/install-github-app` →
5. **Implementação Paralela** com Copilot CLI como reviewer →
6. **Status Sincronizados** back to Plane → Notificação Slack

#### **2.2.3 Human-in-the-Loop Otimizado**

Em vez de aprovações em cada passo (congestionamento), as decisões críticas são agrupadas:

**Auto-aprovável:**
- Refatoração de código (conforme linter + testes)
- Documentação de APIs
- Atualização de dependências menor

**Requer Aprovação Humana:**
- Mudanças arquiteturais
- Alterações de segurança
- Deploys em produção
- Remoção de features

Isso **reduz decisões humanas em 70%** enquanto mantém governança.
```

---

## **📄 SEÇÃO 7: CONTEXT.md**
### **Atualização de Integração: Novos Fluxos de Dados**

```markdown
## **5. Integração com Novo Ecossistema (GitHub Agent HQ + Copilot CLI)**

### **5.1 Fluxo de Arquitetura Expandido**

```
┌─────────────────────────────────────────────────────────────┐
│ Camada de Clientes Unificados                               │
│ • Claude Code (Local Dev)                                   │
│ • GitHub Copilot CLI (Terminal Agent)                       │
│ • OpenWebUI (Web)                                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ├→ GitHub App (/install-github-app)
                   │
┌──────────────────▼──────────────────────────────────────────┐
│ Mission Control (Agent HQ) - Orquestração Central           │
│ • Atribui tarefas a múltiplos agentes                       │
│ • Monitora progresso em tempo real                          │
│ • Escalação automática se falhas > 20%                      │
│ • Dashboard em GitHub Web, VS Code, CLI                     │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────────┐
        │                         │
┌───────▼──────────────┐  ┌──────▼──────────────┐
│ n8n Orchestrator     │  │ LiteLLM Router      │
│ (Event-driven)       │  │ (Model Selection)   │
│ • GitHub Webhooks    │  │ • Copilot CLI       │
│ • Plane API Sync     │  │ • Claude Fallback   │
│ • Document Ingestion │  │ • GPT-5 (soon)      │
└─────────────────────┘  └─────────────────────┘
        │                         │
┌───────┴─────────────────────────┴──────────────┐
│ MCP Servers (Unified Interface Layer)          │
│ • GitHub MCP (Issues, PRs, Commits)            │
│ • Plane MCP (Tasks, Projects)                  │
│ • LightRAG MCP (Knowledge Retrieval)           │
│ • Copilot CLI MCP (Native Integration)         │
└─────────────────────────────────────────────────┘
```

### **5.2 Governança Multi-Plataforma**

O arquivo `AGENTS.md` centraliza:
- Permissões por agente
- Rate limits e quotas
- Audit logging
- Escalation policies
- Onboarding de novos agentes

---

# 📌 Observações Críticas de Implementação

## Ordem de Prioridade para Integração

1. **Imediato (Semana 1-2):**
   - Documentar em `CLAUDE_CODE_GUIDE.md` seção 5 expandida
   - Criar `AGENTS.md` básico
   - Testar `/install-github-app` com Copilot CLI

2. **Curto Prazo (Semana 3-4):**
   - Implementar n8n workflows GitHub ↔ Plane
   - Setup Docker para Copilot CLI como agente persistente
   - Integrar ao LiteLLM Proxy

3. **Médio Prazo (Mês 2):**
   - Mission Control full operacional
   - Power Prompts em produção
   - AGENTS.md com governança completa

4. **Longo Prazo (Mês 3+):**
   - Multi-provider agents (Gemini CLI, etc.)
   - Métricas avançadas de performance
   - Automação 90%+ do pipeline

---

# 🎯 Benefícios Mensuráveis

| Métrica | Baseline | Meta (90 dias) | Impacto |
|---------|----------|----------------|---------|
| **Tempo Feature PR** | 4 horas | 45 minutos | 82% ↓ |
| **Approval Bottlenecks** | 6/dia | 1/dia | 83% ↓ |
| **Code Review Time** | 2h | 15m | 87% ↓ |
| **Bug Discovery (pre-deploy)** | 70% | 95% | 25% ↑ |
| **Developer Context Switching** | 12x/day | 3x/day | 75% ↓ |
| **Automation Coverage** | 40% | 90% | 50% ↑ |

