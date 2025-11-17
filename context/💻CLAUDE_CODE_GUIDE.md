# 💻 Guia de Maestria do Claude Code

> **Nota de Generalização:** Os princípios deste guia, especialmente o framework "Explorar, Planejar, Executar" e as estratégias de gerenciamento de contexto, são universalmente aplicáveis a qualquer agente de desenvolvimento de terminal avançado, incluindo o **Claude Code** e o **GitHub Copilot CLI**.

## **1. A Mudança de Paradigma: De Gerador de Código a Agente de Desenvolvimento**
.

Para desbloquear 90% do valor do Claude Code, é crucial entendê-lo não como um ChatGPT na linha de comando, mas como uma ferramenta agentic capaz de processamento complexo em múltiplos passos. Ele é projetado para gerenciar tarefas de ponta a ponta, desde o planejamento até o pull request.

| Assistentes Tradicionais (ex: Cursor) | Claude Code (Workflow Agentic) |
| :--- | :--- |
| **Caso de Uso Ideal:** Resolver problemas específicos em arquivos ou linhas de código onde o desenvolvedor seleciona o alvo. | **Caso de Uso Ideal:** Executar tarefas grandes e multifacetadas como iniciar projetos, refatorar sistemas complexos ou implementar features. |
| **Modelo Operacional:** Intervenção pontual definida por um humano. | **Modelo Operacional:** Decompõe um objetivo de alto nível em subtarefas, cria um plano e o executa sequencialmente. |

### **1.1 Capacidades Agentic Essenciais**
*   **Processamento Multi-Passo:** Excepcional em processos complexos e de longa duração, consolidando informações de múltiplos arquivos.
*   **Planejamento e Listas de Tarefas:** Gera especificações e checklists para manter o contexto e a direção, essencial para a coordenação entre subtarefas e subagentes.
*   **Loop de Reflexão:** Capacidade de autoavaliar seu próprio output, identificar falhas e se autocorrigir, reduzindo a necessidade de supervisão humana.

## **2. O Framework de Sucesso: Explorar, Planejar, Executar**

O erro mais comum é pular direto para a execução. Para obter resultados de alta qualidade, siga este ciclo:

1.  **Explorar:** Force o Claude a "gastar tokens para construir contexto". Peça para ele ler e analisar os arquivos relevantes, a arquitetura e os requisitos *antes* de escrever qualquer código.
2.  **Planejar:** Peça um plano de implementação detalhado. Use prompts como o "My Developer" (Seção 6.1) para obter feedback crítico. Itere no plano para tarefas de alto risco.
3.  **Executar:** Com um contexto robusto e um plano sólido, instrua o Claude a implementar a solução. O resultado será drasticamente superior.

## **3. Configuração Essencial e Comandos**

### **3.1 Instalação e Modos de Operação**
```bash
# Instalação global
npm install -g @anthropic-ai/claude-code
```
*   **Modos (Ciclar com `Shift + Tab`):**
    *   **Default Edit Mode:** Exige aprovação para cada alteração (seguro).
    *   **Auto Accepted Mode:** Escreve arquivos sem permissão (recomendado em containers).
    *   **Plan Mode:** Pesquisa e planeja sem alterar o código.

### **3.2 Comandos Fundamentais**
*   `/model`: Alterna entre modelos (ex: Sonnet para tarefas rápidas, Opus para raciocínio complexo).
*   `/id`: Conecta ao IDE (configure `autoconnect: true` para automação).
*   `/clear`: Limpa o contexto entre tarefas distintas para evitar "apodrecimento de contexto".
*   `think` / `think harder`: Controla o orçamento de pensamento da IA para tarefas complexas.

## **4. Maestria em Gerenciamento de Contexto**

A qualidade do output é diretamente proporcional à qualidade do contexto.

### **4.1 O Cérebro do Projeto: `claude.md`**
Este arquivo é o "README para o Claude Code", incluído automaticamente nos prompts. Deve ser refinado como qualquer prompt crítico.
*   **Estratégia Avançada:** Crie `claude.md` aninhados em subpastas para fornecer contexto granular sobre microserviços ou componentes específicos.

### **4.2 Arquivos de Contexto Suplementares**
*   **`plan.md`:** Documento que detalha os objetivos para uma nova tarefa ou projeto.
*   **`changelog.md`:** Ajuda o Claude a entender o histórico de mudanças e as razões por trás delas.

### **4.3 Técnicas Avançadas: Fork e Reutilização de Contexto**
*   **`double escape` (Pressionar Esc duas vezes):** "Forka" a conversa, salvando o estado atual do agente com todo o seu contexto.
*   **`/resume`:** Abre uma nova aba de terminal e usa `/resume` para carregar o estado salvo, permitindo trabalhar em uma tarefa paralela com o mesmo agente altamente contextualizado.

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

Para garantir governança e clareza, o arquivo `AGENTS.md`/ `CLAUDE.md` na raiz do projeto centraliza a definição de todos os agentes operacionais.

> **Referência Completa:** Consulte [`AGENTS.md`](AGENTS.md) para a estrutura detalhada e as definições.

Este arquivo define responsabilidades, restrições e integrações para cada agente (Claude Code, Copilot CLI, n8n, etc.), criando uma matriz de responsabilidade clara e auditável.

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


-------------------------------------------------------------------------------

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


## **6. Técnicas Avançadas e Dicas de Produtividade**

### **6.1 O Truque de Prompt "My Developer"**
Para obter feedback mais direto e crítico, em vez de dizer "Este é o meu plano", diga: **"Meu desenvolvedor criou este plano. O que você acha?"**. Isso remove o viés de polidez da IA, que passa a avaliar o plano de um terceiro hipotético de forma mais objetiva.

### **6.2 Desenvolvimento Orientado a Testes (TDD)**
Peça ao Claude para primeiro escrever testes que falham e, em seguida, escrever o código necessário para que eles passem.

### **6.3 Hooks para Qualidade Contínua (`.claude/settings.local.json`)**
Automatize verificações de qualidade para garantir que o agente produza código limpo.
```json
{
  "hooks": [
    { "event": "PostToolUse", "command": "npm run lint:fix" },
    { "event": "PostToolUse", "command": "npm run type-check" }
  ]
}
```

### **6.4 Subagentes como Pesquisadores e Planejadores**
Use subagentes para tarefas de alto consumo de contexto (pesquisa, análise de APIs). Eles operam em um contexto isolado e retornam um plano ou resumo conciso, mantendo o contexto do agente principal limpo e focado na implementação.

### **6.5 Desenvolvimento Paralelo com Git Worktrees**
Explore múltiplas soluções para um problema complexo de forma isolada.
```bash
# Prepara 3 ambientes de implementação paralela para a feature 'auth'
/prep-parallel feature-auth 3

# Executa o desenvolvimento em paralelo com base em um plano
/execute-parallel feature-auth plan.md 3

# Revisa os worktrees e faz o merge da melhor solução
git worktree list
git merge best-implementation-branch
```

## **7. Encapsulando Conhecimento com Comandos Customizados**

Comandos são prompts reutilizáveis salvos em arquivos, permitindo que a equipe padronize e compartilhe workflows complexos. Um engenheiro sênior pode criar um comando para uma análise de segurança, e toda a equipe pode executá-lo com uma única linha.

## **8. Análise de Custo-Benefício**

*   **Investimento:** O plano Max custa um valor fixo por usuário (ex: $200/mês).
*   **Valor Direto:** Este plano pode equivaler a $3.000 a $5.000 em custos de API por mês.
*   **Ganhos de Produtividade:**
    *   **Iniciação de Projetos Acelerada:** Geração de especificações e planos de alta qualidade.
    *   **Revisão de Código Automatizada:** Libera tempo de desenvolvedores sênior.
    *   **Escala Massiva:** Permite que um desenvolvedor gerencie a implementação de múltiplas features simultaneamente.

*(Nota: Todo o conteúdo anterior sobre MCPs, Serena, Permissões, etc., foi preservado e se encaixa logicamente dentro desta nova estrutura.)*
