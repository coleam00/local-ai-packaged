# **Arquitetura do Sistema de Desenvolvimento Assistido por IA**

> Atualizado para refletir: start_services.py, Caddy hostnames, Portainer integrado, LiteLLM externo.

## Mapa da Stack (fonte da verdade)
- Orquestração: `docker-compose.yml` + `start_services.py`
- Banco RAG: Supabase Postgres local (pgvector) — schema copiado de `all-rag-strategies/implementation/sql/schema.sql`
- RAG: `rag-api` (FastAPI) e `rag-ingestion` (perfil `ingestion`)
- Observabilidade: Langfuse (web/worker + Postgres + ClickHouse + MinIO)
- UI/Agentes: Open WebUI, n8n, Flowise
- Conhecimento: Neo4j (para grafos)
- Proxy: Caddy (hostnames configuráveis no `.env`)
- Gestão: Portainer (via Caddy)
- LLM: LiteLLM rodando no host `http://host.docker.internal:4000/v1` (config via `LLM_BASE_URL` e `LITELLM_MASTER_KEY`)

Nota: Archon é módulo desacoplado. Ele usa Supabase Cloud próprio e aponta para LiteLLM local com `LLM_BASE_URL` e `OPENAI_API_KEY` = `LITELLM_MASTER_KEY`.

Este documento descreve a arquitetura de alto nível e o fluxo de dados que sustentam a metodologia BMAD. Ele serve como o mapa central para entender como os componentes do nosso ecossistema interagem.

> **📚 Documentação Relacionada:**
> - [CLAUDE.md](../CLAUDE.md) - Guia completo de comandos e arquitetura para Claude Code
> - [README.md](../README.md) - Visão geral e guia de início rápido do projeto
> - [🗄️DATABASE_SETUP.md](🗄️DATABASE_SETUP.md) - Arquitetura de dados e schemas
> - [🤖LIGHTRAG_IMPLEMENTATION.md](🤖LIGHTRAG_IMPLEMENTATION.md) - Implementação RAG híbrida

## **1. Visão Geral das Camadas**

O sistema é composto por camadas distintas, cada uma com uma responsabilidade clara, garantindo modularidade e escalabilidade.

```mermaid
graph TB
    subgraph INTERFACES["🖥️ Camada de Interação"]
        UI1[Claude Code CLI]
        UI2[OpenWebUI]
        UI3[Plane Web UI]
    end

    subgraph ORCHESTRATION["⚙️ Camada de Orquestração e Automação"]
        MCP[MCP Servers<br/>(Claude Code Tools)]
        N8N[n8n<br/>(Workflows de Ingestão e Automação)]
    end

    subgraph CORE_LOGIC["🧠 Camada de Lógica e Gerenciamento"]
        PLANE[Plane API<br/>(Gestão de Projetos)]
        LIGHTRAG[LightRAG Server<br/>(Recuperação de Contexto)]
        LITELLM[LiteLLM Proxy<br/>(Gateway para LLMs)]
    end

    subgraph STORAGE["💾 Camada de Persistência"]
        SUPABASE[(Supabase<br/>- DB Vetorial (pgvector)<br/>- Auth & Storage)]
        POSTGRES_PLANE[(PostgreSQL<br/>- Banco de Dados do Plane)]
        NEO4J[(Neo4j<br/>- Grafo de Conhecimento)]
    end

    UI1 --> MCP
    UI2 --> LIGHTRAG
    UI3 --> PLANE

    MCP --> LIGHTRAG
    MCP --> PLANE

    N8N --> LIGHTRAG
    N8N --> PLANE

    LIGHTRAG --> LITELLM
    LIGHTRAG --> SUPABASE
    LIGHTRAG --> NEO4J

    PLANE --> POSTGRES_PLANE
```

## **1.1 Arquitetura Dual-Database**

Para garantir estabilidade e desacoplamento, o sistema utiliza **duas instâncias PostgreSQL independentes**:

| Database | Porta | Superuser | Responsabilidade |
|----------|-------|-----------|------------------|
| **supabase-db** | 5432 | supabase_admin | Supabase ecosystem, RAG (LightRAG), n8n, LiteLLM logs |
| **postgres-plane** | 5433 | postgres | Plane project management (isolado) |

**Vantagens desta abordagem:**
- ✅ Desacoplamento total entre serviços
- ✅ Sem conflitos de usuários ou permissões
- ✅ Atualizações seguras e independentes
- ✅ Arquitetura profissional e escalável

**Configuração:**
- Ambos os bancos são orquestrados via `docker-compose.yml`
- Init scripts separados: `config/init-db.sql` (Supabase) e `config/init-plane.sql` (Plane)
- Backups independentes para cada instância

## **2. Jornada de uma Consulta RAG (End-to-End)**

Este é o fluxo completo, desde uma pergunta do desenvolvedor até a resposta enriquecida pelo RAG.

1.  **Prompt do Usuário (Claude Code):** `Como implemento a autenticação com Supabase?`
2.  **Chamada MCP:** O agente Claude Code utiliza a ferramenta `query_knowledge_base`.
3.  **Augmentação de Contexto:** O servidor MCP lê arquivos relevantes do **Memory Bank** (`/memory-bank/system_patterns.md`) e os anexa à consulta.
4.  **API LightRAG:** Envia a consulta aumentada para o endpoint `/query`.
5.  **Extração de Palavras-chave (via LiteLLM):** LightRAG identifica entidades locais ("Supabase", "autenticação") e globais ("segurança", "JWT").
6.  **Recuperação Híbrida (Paralela):**
    *   **Busca Vetorial (Supabase/pgvector):** Procura por similaridade semântica nos documentos fragmentados.
    *   **Travessia de Grafo (Neo4j):** Navega pelas relações entre conceitos (ex: "Supabase" está conectado a "JWT", que está conectado a "Segurança").
7.  **Fusão de Contextos:** LightRAG combina os resultados da busca vetorial e do grafo, ranqueando os mais relevantes.
8.  **Síntese Final (via LiteLLM):** O contexto recuperado é injetado no prompt final, junto com a pergunta original, e enviado ao LLM (Claude/GPT) para gerar uma resposta precisa e contextualizada.
9.  **Resposta ao Usuário:** A resposta final é retornada ao Claude Code.

## **2.1 LiteLLM como Ponte Universal**

O **LiteLLM Proxy** roda no **host** (não no Docker) na porta 4000 e serve como gateway unificado para todos os provedores de LLM:

**Arquitetura:**
```
┌─────────────────────────────────────────────┐
│         LiteLLM Proxy (Host:4000)          │
│  Router Universal para 100+ Provedores LLM │
└──────┬──────────────────────────┬───────────┘
       │                          │
  ┌────▼────────┐         ┌───────▼──────────┐
  │  ai-stack   │         │  Archon (opcional)│
  │  Services   │         │  Services         │
  └─────────────┘         └───────────────────┘
```

**Por que no host?**
- Simplifica roteamento de rede (localhost:4000)
- Facilita debugging durante desenvolvimento
- Acesso direto a credenciais do GitHub Copilot
- Sem complexidade de networking Docker

**Configuração:**
```bash
# Terminal 1 (manter rodando)
cd /home/sedinha/ai-stack
litellm --config config/auto-headers-config.yaml --port 4000
```

## **3. Fluxo de Ingestão de Contexto (n8n)**

A manutenção do nosso RAG é um processo automatizado orquestrado pelo n8n.

1.  **Gatilho:** Um novo documento é adicionado ou atualizado no **Memory Bank** (ex: um commit no repositório Git).
2.  **Processamento (n8n):**
    *   O documento é lido e seu conteúdo é extraído.
    *   É aplicado o **Document Sharding** (usando `@kayvan/markdown-tree-parser`), quebrando-o em pedaços lógicos.
    *   Para cada pedaço (shard), um embedding vetorial é gerado via LiteLLM.
3.  **Persistência Dupla (n8n):**
    *   Os shards e seus embeddings são salvos no **Supabase** para busca vetorial.
    *   O conteúdo é enviado ao **LightRAG**, que extrai entidades e relações para construir/atualizar o grafo de conhecimento no **Neo4j**.

> **🛠️ Guia de Implementação:** Para ver os workflows JSON do n8n e os scripts de configuração, consulte [`⚙️SYSTEM_WORKFLOWS.md`](⚙️SYSTEM_WORKFLOWS.md).

## **4. Integração com o Ecossistema**

*   **Plane:** Atua como o cérebro da gestão de projetos. É auto-hospedado e utiliza sua própria instância PostgreSQL (porta 5433), garantindo isolamento e controle. Os agentes BMAD interagem com ele via API e MCP para automatizar a criação de sprints, issues e o acompanhamento do progresso.
*   **Claude Code:** É a principal interface de desenvolvimento. Sua capacidade de usar ferramentas (MCPs), subagentes e hooks o torna o executor ideal para a metodologia BMAD.
*   **n8n:** O motor de automação que conecta tudo. Lida com a ingestão de dados para o RAG, sincroniza o GitHub com o Plane e pode executar qualquer tarefa agendada ou baseada em gatilhos.
*   **Archon (Opcional):** Sistema modular de gerenciamento de projetos com IA que pode ser integrado via LiteLLM. Roda como stack independente com Supabase Cloud e se comunica com ai-stack apenas através do proxy LiteLLM na porta 4000. Veja [../docs/ARCHON_INTEGRATION.md](../docs/ARCHON_INTEGRATION.md) para detalhes de integração.

## **5. Documentação de Suporte**

Para aprofundar em tópicos específicos, consulte também:

*   **Claude Code Mastery:** [`💻CLAUDE_CODE_GUIDE.md`](guides/CLAUDE_CODE_GUIDE.md) - Domínio do Claude Code para aumento de produtividade 10x
*   **SuperDesign UI/UX:** [`🎨UIUX_SUPERDESIGN.md`](design/UIUX_SUPERDESIGN.md) - Workflow de co-criação de designs de alta fidelidade
*   **Metodologia BMAD:** [`📋BMAD.md`](methodology/BMAD.md) - Framework de desenvolvimento com IA e ciclos ágeis
*   **Workflows do Sistema:** [`⚙️SYSTEM_WORKFLOWS.md`](workflows/SYSTEM_WORKFLOWS.md) - Automações e implementações técnicas

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

## 6. Integração com o Ecossistema GitHub Agent HQ

A arquitetura foi expandida para incorporar orquestração nativa do GitHub, criando um fluxo de trabalho mais coeso e automatizado.

### 6.1 Governança Multi-Plataforma

A governança é centralizada no arquivo [`AGENTS.md`](AGENTS.md), que define permissões, limites e políticas de escalonamento para todos os agentes, garantindo um controle unificado sobre as automações.

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

---

## **7. Integração Opcional: Archon**

O **Archon** é um sistema de gerenciamento de projetos com IA que pode ser integrado opcionalmente ao ai-stack:

**Características:**
- Stack completamente independente
- Banco de dados: Supabase Cloud (separado do ai-stack)
- Comunicação via LiteLLM Proxy (porta 4000)
- Portas: UI (3737), Server (8181), MCP (8051), Agents (8052)

**Quando usar Archon:**
- Necessita de gerenciamento avançado de projetos com IA
- Quer capacidades MCP adicionais para Claude Code
- Precisa de web crawling e análise de código automáticos
- Deseja integração com GitHub para criação automática de tarefas

**Arquitetura de integração:**
```
┌─────────────────────────────────────────┐
│  LiteLLM Proxy (Host:4000)              │
│  Ponte única entre ai-stack e Archon   │
└──────┬────────────────────┬─────────────┘
       │                    │
  ┌────▼────────────┐  ┌────▼─────────────┐
  │   ai-stack      │  │   Archon         │
  │   (Local)       │  │   (Opcional)     │
  │                 │  │                  │
  │ • PostgreSQL    │  │ • Supabase Cloud │
  │ • Neo4j         │  │ • Archon Services│
  │ • LightRAG      │  │ • MCP Server     │
  │ • n8n           │  │                  │
  └─────────────────┘  └──────────────────┘
```

**Guias de integração:**
- [ARCHON_INTEGRATION.md](../docs/ARCHON_INTEGRATION.md) - Setup passo-a-passo
- [ARCHON_VALIDATION.md](../docs/ARCHON_VALIDATION.md) - Scripts de validação
- [Resolvendo Problemas do Archon no Arch Linux](../docs/Resolvendo%20o%20Problema%20do%20Archon%20no%20Arch%20Linux.md) - Troubleshooting

---

**📝 Última Atualização:** 2025-01-28
**🔗 Próximos Passos:** Consulte [CLAUDE.md](../CLAUDE.md) para comandos completos de desenvolvimento

