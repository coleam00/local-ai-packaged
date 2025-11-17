
# **📄 README: O Guia Central da AI-Stack**

Bem-vindo à `ai-stack`, um ecossistema de desenvolvimento integrado, projetado para construir aplicações robustas com assistência de IA. Este documento é o ponto de partida para entender a arquitetura, configurar o ambiente e navegar pela documentação.

## **I. Arquitetura, Configuração e Acesso**

Esta seção contém tudo o que você precisa para começar a usar a stack em minutos.

### **1. Arquitetura Final: Dual-Database (Modular e Escalável)**

A `ai-stack` opera em uma arquitetura de banco de dados dual para garantir estabilidade, segurança e desacoplamento. Esta é uma decisão de design fundamental para a manutenibilidade a longo prazo.

```
┌────────────────────────────────────────────────────────┐
│                     AI-STACK                           │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │  PostgreSQL 15   │      │  PostgreSQL 15   │        │
│  │  (Supabase)      │      │  (Padrão)        │        │
│  │  Porta: 5432     │      │  Porta: 5433     │        │
│  │                  │      │                  │        │
│  │ Superuser:       │      │ Superuser:       │        │
│  │ supabase_admin   │      │ postgres         │        │
│  │                  │      │                  │        │
│  │ ┌────────────┐   │      │ ┌──────────────┐ │        │
│  │ │ RAG Schema │   │      │ │ Plane Schema │ │        │
│  │ │ n8n Schema │   │      │ └──────────────┘ │        │
│  │ └────────────┘   │      │                  │        │
│  └──────────────────┘      └──────────────────┘        │
│                                                        │
│  ✅ Desacoplamento Total | ✅ Sem Conflito de Usuários │
│  ✅ Atualizações Seguras | ✅ Profissional & Escalável │
└─────────────────────────────────────────────────────────┘
```

*   **`supabase-db` (Porta 5432):** O coração da stack de IA. Hospeda o ecossistema Supabase, o schema RAG para `LightRAG`, e os dados do `n8n`.
*   **`postgres-plane` (Porta 5433):** Uma instância PostgreSQL padrão e isolada, dedicada exclusivamente à ferramenta de gerenciamento de projetos `Plane`.

### **2. Guia de Início Rápido (Getting Started)**

1.  **Pré-requisitos:** Docker e Docker Compose instalados.
2.  **Configuração:** Renomeie `env.example` para `.env` e preencha as variáveis de ambiente necessárias.
3.  **Subir a Stack:**
    ```bash
    # Baixa todas as imagens necessárias
    docker-compose pull

    # Sobe todos os serviços em background
    docker-compose up -d
    ```
4.  **Validação:** A inicialização completa pode levar alguns minutos. Monitore os logs para verificar se todos os serviços estão saudáveis:
    ```bash
    docker-compose logs -f
    ```
    Quando os logs se estabilizarem, execute `docker-compose ps` para confirmar que todos os contêineres estão no estado `running` ou `healthy`.

### **3. Acessando os Serviços**

| Serviço | URL | Credenciais / Notas |
| :--- | :--- | :--- |
| **Supabase Studio** | `http://localhost:3000` | Interface web para gerenciar o banco `supabase-db`. |
| **OpenWebUI** | `http://localhost:3001` | Interface de Chat para interagir com os LLMs. |
| **Plane** | `http://localhost:3002` | Gerenciamento de Projetos. |
| **LiteLLM UI** | `http://localhost:4001` | Dashboard do LiteLLM Proxy. |
| **n8n** | `http://localhost:5678` | Automação de Workflows. (user: `admin`, pass: do `.env`) |
| **Neo4j Browser** | `http://localhost:7474` | Gerenciamento do Grafo. (user: `neo4j`, pass: do `.env`) |
| **Supabase API** | `http://localhost:8000` | API Gateway (Kong). Use a `ANON_KEY` do `.env`. |
| **Portainer** | `http://localhost:9000` | Gerenciamento de Contêineres Docker. |
| **MinIO Console** | `http://localhost:9001` | Console de storage do Plane. (creds do `.env`) |
| **LightRAG API** | `http://localhost:9621` | API do sistema RAG. |

### **4. Hub de Documentação**

Navegue pela documentação para entender cada componente em detalhes:
*   **[CONTEXT_ENGINEERING.md](./principles/CONTEXT_ENGINEERING.md):** 🧠 Os **princípios teóricos** por trás da gestão de contexto para agentes de IA.
*   **[DATABASE_SETUP.md](./database/DATABASE_SETUP.md):** 🗄️ A **arquitetura de dados**, o schema RAG completo e como validar a persistência.
*   **[LIGHTRAG_IMPLEMENTATION.md](./implementation/LIGHTRAG_IMPLEMENTATION.md):** 🤖 Detalhes sobre a **implementação do nosso sistema RAG** híbrido e multimodal.
*   **[LLM_INTEGRATION.md](./implementation/LLM_INTEGRATION.md):** 🧠 Como a `ai-stack` se conecta a modelos de linguagem através do **LiteLLM Proxy**.
*   **[CLAUDE_CODE_GUIDE.md](./guides/CLAUDE_CODE_GUIDE.md):** 💻 **Guia avançado** do Claude Code com técnicas de produtividade 10x.
*   **[UIUX_SUPERDESIGN.md](./design/UIUX_SUPERDESIGN.md):** 🎨 Processo de **design iterativo** e workflows de UI/UX com SuperDesign.
*   **[BMAD.md](./methodology/BMAD.md):** 📋 Metodologia **Build with AI, Develop with Agile** para desenvolvimento assistido.
*   **[SYSTEM_WORKFLOWS.md](./workflows/SYSTEM_WORKFLOWS.md):** ⚙️ **Workflows de automação** e implementação técnica do sistema.

---

## **II. Visão Arquitetural Detalhada**

Esta seção aprofunda os conceitos e metodologias que governam a `ai-stack`.

### **1. Arquitetura Modular de 5 Camadas (Visão Conceitual)**

A stack organiza-se em cinco domínios interconectados para uma clara separação de responsabilidades:

| Camada | Tecnologia Principal | Função Central |
| :--- | :--- | :--- |
| **1. Conhecimento (RAG)** | LightRAG + Supabase (PGVector) + Neo4j | Recuperação Híbrida e Grafos de Conhecimento. |
| **2. Desenvolvimento (IDE)** | OpenWebUI + Agentes (Claude Code) | Interface para interação com LLMs. |
| **3. Gerenciamento (PM)** | Plane | Gerenciamento de projetos com metodologia BMAD. |
| **4. Observabilidade** | (Conceitual) highlight.io | Monitoramento de performance de agentes AI. |
| **5. Storytelling** | n8n Workflows + LLM | Automação de conteúdo a partir de métricas e documentos. |

### **2. Fluxos de Trabalho Automatizados**

#### **2.1. Consulta RAG (Jornada End-to-End)**
1.  **Prompt do Usuário** → OpenWebUI/Agente.
2.  **Chamada API** → LightRAG (`ai-lightrag`).
3.  **Recuperação Híbrida:** Busca vetorial no `supabase-db` e travessia de grafo no `ai-neo4j`.
4.  **Síntese:** LLM (via LiteLLM) gera a resposta com o contexto recuperado.
5.  **Resposta Final** → Usuário.

#### **2.2. Ingestão de Documentos (Pipeline Automatizado)**
1.  **Trigger** → Novo arquivo via `n8n`.
2.  **Idempotência** → Verificação de hash no `supabase-db` para evitar duplicatas.
3.  **API LightRAG** → `POST /documents/file` para o serviço `ai-lightrag`.
4.  **Pipeline Multimodal:** Extração de texto, análise de imagens (VLM) e tabelas.
5.  **Persistência Híbrida:** Indexação no `supabase-db` (vetores) e `ai-neo4j` (grafos).

### **3. Metodologias de Desenvolvimento Agêntico**
*   **BMAD (Build with AI, Develop with Agile):** Utiliza o `Plane` para transformar requisitos em issues de desenvolvimento detalhadas de forma automatizada.
*   **SuperDesign:** Workflow de co-criação de UI/UX de alta fidelidade, usando código-fonte real como referência para replicação pixel-perfect.
*   **Gestão Estratégica de Contexto:** Técnicas como fragmentação de documentos (Sharding) e uso do sistema de arquivos (`memory-bank`) como memória externa para os agentes.

---

## **III. Detalhes de Implementação**

### **1. Gerenciamento dos Bancos de Dados**

Com a arquitetura dual, é crucial mirar no contêiner correto para cada tarefa.

#### **Conexão Direta (psql)**

*   **Para o banco Supabase (RAG, n8n):**
    ```bash
    # Use a senha de DB_PASSWORD do seu .env
    docker exec -it supabase-db psql -U supabase_admin -d postgres
    ```
*   **Para o banco do Plane:**
    ```bash
    # Use a senha de POSTGRES_PASSWORD_PLANE do seu .env
    docker exec -it postgres-plane psql -U postgres -d plane_db
    ```

#### **Backup e Restauração**

*   **Backup do Supabase (RAG, n8n):**
    ```bash
    docker exec supabase-db pg_dumpall -U supabase_admin > backup_supabase_$(date +%Y%m%d).sql
    ```
*   **Backup do Plane:**
    ```bash
    docker exec postgres-plane pg_dumpall -U postgres > backup_plane_$(date +%Y%m%d).sql
    ```

### **2. Mapeamento de Serviços (docker-compose)**

A tabela a seguir mapeia os serviços do `docker-compose.yml` para as camadas arquiteturais.

| Serviço (`container_name`) | Camada(s) | Propósito na Arquitetura |
| :--- | :--- | :--- |
| `supabase-db` | 1. Conhecimento | **(Banco Principal)**. Armazena dados do Supabase, vetores (pgvector) para RAG e dados do n8n. |
| `postgres-plane` | 3. Gerenciamento | **(Banco Isolado)**. Dedicado exclusivamente para os dados da aplicação Plane. |
| `ai-neo4j` | 1. Conhecimento | Armazena o Grafo de Conhecimento para o LightRAG. |
| `ai-lightrag` | 1. Conhecimento | Orquestrador RAG, gerenciando consultas híbridas. |
| `ai-n8n` | 5. Storytelling | Hub de automação para ingestão de documentos e outros workflows. |
| `ai-openwebui` | 2. Desenvolvimento | Interface de chat (UI) primária para interagir com os LLMs. |
| `ai-plane-services...` | 3. Gerenciamento | Todos os serviços relacionados ao `Plane` (API, web, workers, etc.). |
| `ai-portainer` | (Utilitário) | Interface de gerenciamento de contêineres Docker. |
| **(Externo)** | 1. Conhecimento | **LiteLLM Proxy (Host)**. Dependência crítica que atua como gateway unificado para os LLMs. |