# Guia de Operações: Local AI Packaged (Arquitetura RAG V2)

Este documento é o seu guia central para entender, operar e desenvolver no ecossistema `local-ai-packaged`. Ele foi completamente reescrito para refletir a nova arquitetura implementada, focada em uma estratégia de RAG (Retrieval-Augmented Generation) avançada e modular.

## 1. Visão Geral da Arquitetura

O projeto agora opera em uma arquitetura de múltiplos serviços, com uma clara separação de responsabilidades:

- **Core RAG (Estratégia Principal)**: O coração do sistema é a nova implementação de RAG do diretório `all-rag-strategies/`. Ela utiliza um banco de dados **PostgreSQL com a extensão pgvector** (rodando via Supabase local) para armazenamento e busca vetorial.
- **Orquestração e Ingestão (n8n)**: O **n8n** é o motor central para a ingestão de dados e orquestração do agente RAG. O novo workflow (`Local_RAG_AI_Agent_n8n_Workflow.json`) define um agente poderoso que pode usar diferentes ferramentas (busca vetorial, SQL, etc.) para responder a perguntas.
- **Interface de Chat (Open WebUI)**: A interação do usuário com o agente RAG é feita através do **Open WebUI**, que se conecta ao n8n por meio do script `n8n_pipe.py`.
- **Módulo Archon (Serviço Separado)**: O **Archon** agora funciona como um módulo independente e integrado. Ele utiliza seu **próprio banco de dados na nuvem Supabase** (configurado no `.env`) e é iniciado junto com os outros serviços, mas opera de forma isolada.
- **Gerenciamento de Modelos (LiteLLM)**: O LiteLLM continua sendo o gateway preferencial para gerenciar o acesso a diferentes modelos de LLM, sejam eles locais (Ollama) ou via API (OpenAI, Anthropic).

## 2. Alinhamento do Tech Stack com as Melhores Práticas de 2025

**Foundation (Core Infrastructure)**:
- ✅ **PostgreSQL (Supabase)** - Banco de dados primário com pgvector
- ✅ **Redis (Valkey)** - Cache e performance
- ✅ **n8n** - Automação de workflows em produção

**AI Agent Tools**:
- ✅ **PydanticAI** - Framework para agentes únicos (a ser integrado)
- ✅ **LangGraph** - Orquestração multi-agente (a ser integrado)
- 🔄 **Arcade** - Autorização de ferramentas (planejado)
- ✅ **Langfuse** - Observabilidade e monitoramento

**RAG Implementation**:
- ✅ **Docling** - Extração de PDFs e documentos
- ✅ **Crawl4AI** - Web scraping e extração de dados
- ✅ **PostgreSQL + pgvector** - Armazenamento vetorial
- 🔄 **Mem0** - Memória de longo prazo (a ser integrado)
- ✅ **Neo4j + Graphiti** - Framework de knowledge graph
- 🔄 **Ragas** - Avaliação de RAG (a ser integrado)
- ✅ **Brave Search** - Integração com busca web
- 🔄 **Perplexity** - Busca avançada (planejado com conta PRO)

**Web Automation**:
- ✅ **Crawl4AI** - Extração de dados web
- 🔄 **Browserbase** - Automação avançada de browser (planejado)

**Self-Hosting Stack**:
- ✅ **LiteLLM** - Serviço local de LLM com endpoints especializados
- ✅ **Open WebUI** - Plataforma local de chat
- ⚠️ **Ollama (legado)** - Sendo gradualmente substituído pelo LiteLLM

## 3. Arquitetura

### Design de Alto Nível do Sistema

```
┌─────────────────────────────────────────────────────────┐
│              ECOSSISTEMA LOCAL-AI-PACKAGED              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │  PostgreSQL 17   │      │   Neo4j 5        │        │
│  │  (Supabase)      │      │  (Knowledge      │        │
│  │  Porta: 5432     │      │   Graph)         │        │
│  │                  │      │  Porta: 7474     │        │
│  │ • pgvector       │      │  Bolt: 7687      │        │
│  │ • Schema RAG     │      │                  │        │
│  │ • Schema n8n     │      │ • Graphiti       │        │
│  │ • Auth (futuro)  │      │ • Entidades      │        │
│  └──────────────────┘      │ • Relações       │        │
│                            └──────────────────┘        │
│                                                         │
│  ┌──────────────────────────────────────────┐          │
│  │     LiteLLM (Porta 4000)                 │          │
│  │  Gateway Universal & Serviço LLM         │          │
│  │  • API de Embedding (dedicada)           │          │
│  │  • Chat Completions                      │          │
│  │  • Roteamento multi-provider             │          │
│  └──────────────────────────────────────────┘          │
│         ▲                    ▲                          │
│         │                    │                          │
│  ┌──────┴────────┐    ┌──────┴─────────┐               │
│  │     n8n       │    │  Open WebUI    │               │
│  │  Porta: 5678  │    │  Porta: 8080   │               │
│  │               │    │                │               │
│  │ • Workflows   │    │ • Chat UI      │               │
│  │ • Pipeline RAG│    │ • Funções      │               │
│  │ • Automação   │    │ • Pipelines    │               │
│  └───────────────┘    └────────────────┘               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Mapa de Camadas de Serviço

| Serviço | Porta | Propósito | Componente do Stack |
|---------|-------|-----------|---------------------|
| **n8n** | 5678 | Automação de workflows & orquestração RAG | Core |
| **Open WebUI** | 8080 | Interface de chat & interação LLM | Interface |
| **LiteLLM** | 4000 | Serviço local de LLM & roteamento | AI Core |
| **PostgreSQL (Supabase)** | 5432 | Banco de dados primário + vetor store | Data |
| **Neo4j** | 7474/7687 | Banco de dados de knowledge graph | RAG |
| **Langfuse** | 3000 | Observabilidade & monitoramento de agentes | Ops |
| **Flowise** | 3001 | Construtor visual de agentes (legado) | Tools |
| **Qdrant** | 6333 | Banco de dados vetorial (alternativa) | RAG |
| **SearXNG** | 8080 | Motor de busca privado | Tools |
| **Caddy** | 80/443 | Proxy reverso & HTTPS | Infra |

### Stack de Tecnologia

**Serviços Core:**
- **n8n**: Automação central de workflows e orquestração de pipeline RAG
- **Supabase (PostgreSQL 17)**: Banco de dados primário com pgvector para embeddings
- **Neo4j 5**: Banco de dados de grafos para relacionamentos de conhecimento com framework Graphiti
- **LiteLLM**: Serviço local de LLM com endpoints de API especializados
- **Open WebUI**: Interface de chat com suporte a funções/pipelines
- **Langfuse**: Plataforma de observabilidade e avaliação de LLM

**Stack RAG:**
- **Graphiti**: Framework moderno de knowledge graph (substitui LightRAG)
- **pgvector**: Busca por similaridade vetorial no PostgreSQL
- **Mem0**: Gerenciamento de memória de longo prazo (planejado)
- **Docling**: Extração de documentos (PDFs, tabelas, diagramas)
- **Crawl4AI**: Web scraping e extração de dados
- **Ragas**: Framework de avaliação RAG (planejado)

**Infraestrutura:**
- **Docker Compose**: Orquestração de serviços
- **Caddy**: Proxy reverso com HTTPS automático
- **Valkey (Redis)**: Cache de alta performance
- **GitHub Actions**: Automação CI/CD
- **Portainer**: Container management UI

**Frameworks de Agentes (A Ser Integrados):**
- **PydanticAI**: Desenvolvimento de agente único
- **LangGraph**: Orquestração multi-agente
- **Arcade**: Autorização de ferramentas (planejado)

## 4. Estratégia de Implementação RAG

### Arquitetura: RAG Híbrido com Graphiti

O sistema implementa uma abordagem **RAG híbrido moderno**:

1. **Busca Vetorial** (PostgreSQL pgvector)
   - Similaridade semântica usando embeddings
   - Indexação HNSW para busca aproximada do vizinho mais próximo rápida
   - Melhor para: Buscas conceituais e temáticas

2. **Busca em Grafo** (Neo4j + Graphiti)
   - Travessia de entidades e relacionamentos
   - Framework moderno de knowledge graph
   - Extração automática de entidades e mapeamento de relações
   - Melhor para: Consultas contextuais e relacionais

3. **Busca de Texto Completo** (PostgreSQL tsvector)
   - Buscas por palavra-chave e correspondência exata
   - Indexação GIN para performance
   - Melhor para: Terminologia específica e trechos de código

### Graphiti vs LightRAG

**Por que Graphiti?**
- ✅ Manutenção ativa (desenvolvimento do LightRAG desacelerou)
- ✅ Melhor documentação e suporte da comunidade
- ✅ Extração de entidades/relacionamentos mais flexível
- ✅ Integração nativa com LangChain
- ✅ Pronto para produção com tratamento adequado de erros

**Caminho de Migração:**
Todas as referências ao LightRAG neste codebase devem ser substituídas pela implementação do Graphiti.

### Fluxo de Dados

```
Pipeline de Ingestão de Documentos:
┌──────────────┐
│   n8n        │ ← Trigger (webhook, upload de arquivo, agendamento)
│   Workflow   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Docling /   │ ← Extrai conteúdo (PDFs, documentos, web)
│  Crawl4AI    │
└──────┬───────┘
       │
       ├─────────────────────────┐
       │                         │
       ▼                         ▼
┌──────────────┐         ┌──────────────┐
│  Graphiti    │         │  PostgreSQL  │
│  (Neo4j)     │         │  (pgvector)  │
│              │         │              │
│ • Entidades  │         │ • Chunks     │
│ • Relações   │         │ • Embeddings │
└──────────────┘         └──────────────┘

Processamento de Consulta:
┌──────────────┐
│  Open WebUI  │ ← Consulta do usuário
│  ou n8n      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  LiteLLM     │ ← Gera embedding da consulta
│  (Embedding) │
└──────┬───────┘
       │
       ├─────────────────────────┐
       │                         │
       ▼                         ▼
┌──────────────┐         ┌──────────────┐
│  Graphiti    │         │  PostgreSQL  │
│  Consulta    │         │  Busca       │
│              │         │  Vetorial    │
└──────┬───────┘         └──────┬───────┘
       │                        │
       └────────┬───────────────┘
                │
                ▼
         ┌──────────────┐
         │  LiteLLM     │ ← Sintetiza resposta com contexto
         │  (Chat)      │
         └──────────────┘
```

## 5. Configuração Essencial (`.env`)

O arquivo `.env` na raiz do projeto é a fonte única de configuração para todos os serviços. As seções mais importantes são:

#### Configuração Global e do Agente RAG
```env
# --- LiteLLM & AI Models ---
LITELLM_MASTER_KEY=sk-auto-headers-2025
OPENAI_API_KEY=your-openai-api-key # ESSENCIAL: Usado pelo agente RAG e n8n
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key

# --- Modelos para o Agente RAG ---
LLM_CHOICE=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# --- Banco de Dados Local (Supabase/Postgres para RAG) ---
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_PASSWORD=rag_super_secure_password_2025 # Altere esta senha
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD} @${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
```

#### Configuração do Módulo Archon
```env
# --- Banco de Dados do Archon (Supabase Cloud) ---
# Obtenha estes valores do seu projeto no Supabase Cloud
SUPABASE_URL=https://nrvobbjftbzidokjhamw.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# --- LLM do Archon (Redirecionado para o LiteLLM local) ---
LLM_BASE_URL=http://host.docker.internal:4000/v1
```

## 6. Como Executar o Projeto

O script `start_services.py` continua sendo a forma recomendada de iniciar o ambiente.

```bash
# Iniciar todos os serviços (com perfil de GPU, se aplicável)
python start_services.py --profile gpu-nvidia

# Iniciar em um ambiente apenas com CPU
python start_services.py --profile cpu

# Parar todos os serviços
docker compose -p localai down

# PARAR E DESTRUIR OS DADOS (use com cuidado!)
# Isso removerá os volumes do Docker, incluindo os dados do seu banco de dados RAG.
# É útil para reiniciar o banco de dados do zero e aplicar o novo schema.sql.
docker compose -p localai down -v
```

## 7. O Novo Sistema RAG

Esta é a mudança mais significativa. O sistema RAG agora funciona de duas maneiras principais:

### 7.1. Interação via Interface Gráfica (Open WebUI + n8n)

Esta é a forma principal de interagir com o agente.

- **Como Funciona**: Você envia uma mensagem no Open WebUI. O script `n8n_pipe.py` encaminha sua mensagem para o webhook do n8n. O workflow `RAG_AI_Agent_Template_V5` é acionado, usando suas ferramentas (busca vetorial no Postgres, etc.) para encontrar a resposta e devolvê-la à interface.
- **Ingestão de Dados**: O workflow do n8n está configurado para monitorar uma pasta no Google Drive. Ao adicionar um arquivo (PDF, TXT, etc.) nessa pasta, o n8n automaticamente o processa, gera os embeddings e o insere no banco de dados vetorial (Postgres).
- **Setup Necessário**:
    1. No n8n (http://localhost:5678), você precisará configurar as credenciais para:
        - **PostgreSQL**: Use os dados do `.env` (`host: db`, `user: postgres`, `password: ${POSTGRES_PASSWORD}`).
        - **OpenAI**: Use sua chave da API.
        - **Google Drive**: Autentique com sua conta Google.
    2. Na primeira vez, execute manualmente os nós de criação de tabela no workflow do n8n para garantir que a estrutura do banco de dados esteja correta.

### 7.2. Interação via Linha de Comando (CLI)

Para desenvolvedores e testes avançados, você pode usar o agente RAG diretamente pelo terminal.

- **Como Funciona**: O script `all-rag-strategies/implementation/rag_agent_advanced.py` é um cliente de linha de comando poderoso que interage diretamente com o banco de dados RAG.
- **Como Usar**:
  ```bash
  # Execute o agente a partir da raiz do projeto
  python -m all-rag-strategies.implementation.rag_agent_advanced --query "Qual é o resumo do documento X?"
  ```
- **Observação**: Este script utiliza as variáveis de ambiente `DATABASE_URL`, `LLM_CHOICE`, e `EMBEDDING_MODEL` definidas no seu arquivo `.env`.

## 8. Módulo Archon

- **Independência**: O Archon agora é um "vizinho" dos outros serviços, não o centro. Ele é iniciado pelo `docker-compose.yml` principal, mas usa seu próprio `docker-compose.yml` (`Archon/docker-compose.yml`) e se conecta a um banco de dados na nuvem, conforme definido no `.env`.
- **Comunicação**: Ele se comunica com o LiteLLM local para requisições de LLM, o que permite que ele se beneficie do gerenciamento centralizado de modelos.

## 9. Comandos Úteis

```bash
# Ver os logs de todos os contêineres
docker compose -p localai logs -f

# Ver os logs de um serviço específico (ex: n8n)
docker compose -p localai logs -f n8n

# Acessar o banco de dados RAG (Postgres)
docker compose -p localai exec db psql -U postgres

# Dentro do psql, você pode verificar as tabelas do RAG:
\dt public.*

# E verificar se a extensão pgvector está ativa:
\dx vector
```

---
**Última Atualização:** 2025-11-09
**Versão do Projeto:** 3.0 (Arquitetura RAG V2)