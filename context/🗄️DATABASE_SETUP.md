# **🗄️ Arquitetura de Dados: Configuração e Schema**

Este documento detalha a camada de persistência da `ai-stack`, baseada em uma arquitetura de banco de dados dual, e fornece o schema completo para o sistema RAG.

## **1. Visão Arquitetural: Dual-Database**

Para garantir estabilidade e desacoplamento, a `ai-stack` utiliza duas instâncias PostgreSQL independentes, orquestradas via `docker-compose.yml`.

| Característica | **Database 1: Supabase (RAG & Core)** | **Database 2: PostgreSQL Padrão (Plane)** |
| :--- | :--- | :--- |
| **Contêiner** | `supabase-db` | `postgres-plane` |
| **Porta Exposta** | `5432` | `5433` |
| **Superusuário** | `supabase_admin` | `postgres` |
| **Responsabilidade** | Supabase, RAG (LightRAG), n8n, LiteLLM Logs | Exclusivamente para o Plane Project Management |
| **Vantagens** | Ecossistema Supabase completo (Auth, Storage, API) | Isolamento total, sem conflitos de versão ou usuário |

### **Decisão Arquitetural: Por que Dual-Database?**

**Problema:** Plane requer configurações específicas do PostgreSQL e roles de usuário que conflitam com o setup opinado do Supabase.

**Solução:** Separar em duas instâncias completamente independentes:
- **supabase-db** (5432): Core do ai-stack (RAG, n8n, Supabase services)
- **postgres-plane** (5433): Isolado para Plane

**Benefícios:**
- ✅ Zero conflitos de usuários/roles
- ✅ Escalabilidade independente
- ✅ Upgrades seguros (atualizar um sem afetar o outro)
- ✅ Backups e recovery isolados
- ✅ Clareza na separação de responsabilidades

### **1.1 Arquitetura de Três Camadas (com Archon Opcional)**

Quando o **Archon** é integrado, o sistema opera com três bases de dados:

```
┌──────────────────────────────────────────────┐
│            LiteLLM Proxy (Host)              │
│         Gateway Unificado de LLMs            │
└───┬──────────────────────┬──────────────┬────┘
    │                      │              │
┌───▼───────────┐  ┌───────▼──────┐  ┌───▼────────────┐
│ supabase-db   │  │postgres-plane│  │ Supabase Cloud │
│ (ai-stack)    │  │ (ai-stack)   │  │ (Archon)       │
│               │  │              │  │                │
│ Port: 5432    │  │ Port: 5433   │  │ Port: Cloud    │
│               │  │              │  │                │
│ • RAG Schema  │  │ • Plane      │  │ • Archon       │
│ • n8n Schema  │  │   Schema     │  │   Schemas      │
│ • Supabase    │  │              │  │ • Projects     │
│   Services    │  │              │  │ • Tasks        │
└───────────────┘  └──────────────┘  └────────────────┘
```

**Nota:** Archon é **completamente opcional** e roda de forma independente. A integração é feita apenas via LiteLLM.

## **2. Schema do Banco de Dados RAG (em `supabase-db`)**

O schema a seguir é aplicado automaticamente ao contêiner `supabase-db` através do script `config/init-db.sql`. Ele cria a estrutura necessária para o LightRAG e o pipeline de ingestão.

> **Nota:** O `search_path` é ajustado para incluir o schema `extensions`, garantindo que tipos como `VECTOR` e funções como `uuid_generate_v4()` funcionem corretamente no ambiente Supabase.

```sql
-- =====================================================
-- INIT-DB.SQL - AI-STACK + SUPABASE (Versão 3.4)
-- =====================================================

-- Garante que as extensões do Supabase estejam no caminho de busca
SET search_path TO public, extensions, "$user";

-- Schema principal para toda a lógica RAG
CREATE SCHEMA IF NOT EXISTS rag;

-- Tipos ENUM para status e tipos de chunk
CREATE TYPE rag.doc_processing_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'PAUSED');
CREATE TYPE rag.chunk_type AS ENUM ('text', 'code', 'table', 'image', 'formula');

-- Tabela de fontes de documentos
CREATE TABLE IF NOT EXISTS rag.sources (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  url TEXT UNIQUE NOT NULL,
  source_type VARCHAR(50) NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de documentos com hash para idempotência
CREATE TABLE IF NOT EXISTS rag.documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_id UUID REFERENCES rag.sources(id) ON DELETE CASCADE,
  doc_hash VARCHAR(64) UNIQUE NOT NULL,
  source_uri TEXT NOT NULL,
  filename TEXT,
  file_type VARCHAR(50),
  title TEXT,
  version INTEGER DEFAULT 1,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de status de processamento
CREATE TABLE IF NOT EXISTS rag.doc_status (
  document_id UUID PRIMARY KEY REFERENCES rag.documents(id) ON DELETE CASCADE,
  status rag.doc_processing_status DEFAULT 'PENDING',
  last_error TEXT,
  processing_log JSONB DEFAULT '{}'::jsonb,
  progress DECIMAL(5,2) DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de chunks (o coração do RAG)
CREATE TABLE IF NOT EXISTS rag.chunks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chunk_hash VARCHAR(64) UNIQUE NOT NULL,
  document_id UUID NOT NULL REFERENCES rag.documents(id) ON DELETE CASCADE,
  chunk_order_index INT NOT NULL,
  chunk_type rag.chunk_type DEFAULT 'text',
  content TEXT NOT NULL,
  cleaned_content TEXT,
  embedding VECTOR(1536), -- Dimensão para text-embedding-3-small
  fts_vector TSVECTOR,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(document_id, chunk_order_index)
);

-- Índice HNSW para busca vetorial de alta performance
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
  ON rag.chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m=16, ef_construction=64);

-- Índice GIN para Full-Text Search
CREATE INDEX IF NOT EXISTS idx_chunks_fts
  ON rag.chunks
  USING gin(fts_vector);

-- (O script completo em config/init-db.sql inclui mais tabelas, views e triggers)
```

## **3. Validação da Configuração**

Após iniciar a stack com `docker-compose up -d`, use os seguintes comandos para validar se os bancos de dados estão configurados corretamente.

### **Validar `supabase-db` (RAG)**
```bash
# Conectar ao contêiner
docker exec -it supabase-db psql -U supabase_admin -d postgres

# Dentro do psql, verificar as tabelas do schema RAG
\dt rag.*
```
**Saída esperada:** Uma lista de tabelas como `chunks`, `documents`, `sources`, etc.

### **Validar `postgres-plane` (Plane)**
```bash
# Conectar ao contêiner
docker exec -it postgres-plane psql -U postgres

# Dentro do psql, verificar se o banco de dados 'plane_db' existe
\l
```
**Saída esperada:** Uma lista de bancos de dados que inclui `plane_db`. O Plane criará suas próprias tabelas automaticamente na primeira execução.

---

## **4. Archon Database (Opcional - Supabase Cloud)**

Se você optar por integrar o **Archon** ao seu ecossistema, ele utilizará um banco de dados **completamente separado** no Supabase Cloud.

### **4.1 Por que Supabase Cloud para Archon?**

**Decisão Arquitetural:**
- ✅ Isolamento total do ai-stack local
- ✅ Sem conflitos de schema ou portas
- ✅ Escalabilidade gerenciada pela Supabase
- ✅ Backups automáticos
- ✅ Interface web para gerenciamento

### **4.2 Schema do Archon**

O Archon utiliza as seguintes tabelas principais:

```sql
-- Tabelas principais do Archon
archon_projects              -- Gerenciamento de projetos
archon_tasks                 -- Tracking de tarefas
archon_sources               -- Fontes de conhecimento
archon_crawled_pages         -- Dados de web crawling
archon_code_examples         -- Exemplos de código extraídos
archon_agent_work_orders     -- Orders de trabalho para agentes
archon_configured_repositories -- Repositórios configurados
```

### **4.3 Configuração do Archon Database**

**Passo 1: Criar Projeto Supabase**
```bash
# Acesse https://supabase.com/dashboard
# Crie um novo projeto gratuito
# Anote:
# - Project URL: https://seu-projeto.supabase.co
# - Service Role Key: eyJhbGci... (chave longa)
```

## **Passo 2: Executar Migrations**

Fluxo atual (automatizado via `start_services.py`):
1) Copia `all-rag-strategies/implementation/sql/schema.sql` para `supabase/docker/volumes/db/init/02-rag-schema.sql`
2) Sobe Supabase e aguarda o `db` ficar pronto (`pg_isready`)
3) Se necessário, aplica schema em runtime via `docker exec psql`

Verificação:
- `docker compose -p localai -f supabase/docker/docker-compose.yml exec db psql -U postgres -d postgres -c "\\dt"`
- Extensão pgvector: `\dx vector`

Portainer: use a UI para ver os containers `db`, logs e saúde.

```bash
# Navegue até as migrations do Archon
cd /home/sedinha/ai-stack/Archon/migration/0.1.0

# Abra o Supabase SQL Editor
# Execute os scripts na ordem:
# 1. backup_database.sql (opcional, para backups)
# 2. 001_add_source_url_display_name.sql
# 3. 002_add_hybrid_search_tsvector.sql
# 4. 003_ollama_add_columns.sql
# 5. 004_ollama_migrate_data.sql
# 6. 005_ollama_create_functions.sql
# 7. 006_ollama_create_indexes_optional.sql
# 8. 007_add_priority_column_to_tasks.sql
# 9. 008_add_migration_tracking.sql

# Ou execute o script completo:
# complete_setup.sql
```

**Passo 3: Configurar .env do Archon**
```bash
# Em /home/sedinha/ai-stack/Archon/.env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGci... # Service role key

# IMPORTANTE: Redirecionar LLM para LiteLLM
OPENAI_BASE_URL=http://host.docker.internal:4000/v1
OPENAI_API_KEY=sk-auto-headers-2025  # Usar LITELLM_MASTER_KEY
```

### **4.4 Validação do Archon Database**

```bash
# Verificar se tabelas foram criadas
# No Supabase SQL Editor:
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'archon_%'
ORDER BY table_name;

# Esperado: Lista com todas as tabelas archon_*
```

### **4.5 Comandos Úteis - Archon**

```bash
# Verificar conectividade do Archon ao banco
docker compose -f ~/ai-stack/Archon/docker-compose.yml logs archon-server | grep -i "database\|supabase"

# Testar conexão manualmente
docker compose -f ~/ai-stack/Archon/docker-compose.yml exec archon-server \
  curl -v https://seu-projeto.supabase.co

# Ver estatísticas das tabelas
# No Supabase SQL Editor:
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
  n_live_tup AS rows
FROM pg_stat_user_tables
WHERE tablename LIKE 'archon_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## **5. Mapa Completo de Portas e Conexões**

| Componente | Host | Container | Banco de Dados | Porta DB |
|------------|------|-----------|----------------|----------|
| **LightRAG** | localhost | ai-lightrag | supabase-db | 5432 |
| **n8n** | localhost | ai-n8n | supabase-db | 5432 |
| **Plane API** | localhost | ai-plane-api | postgres-plane | 5433 |
| **Supabase Studio** | localhost:3000 | supabase-studio | supabase-db | 5432 |
| **Neo4j** | localhost:7474 | ai-neo4j | - (graph DB) | 7687 |
| **Archon Server** | localhost:8181 | archon-server | Supabase Cloud | Cloud |
| **Archon UI** | localhost:3737 | archon-ui | - (frontend) | - |

---

## **6. Backup Strategy**

### **6.1 Backup ai-stack Databases**

```bash
# Backup Supabase database
docker exec supabase-db pg_dumpall -U supabase_admin > \
  backups/supabase_$(date +%Y%m%d_%H%M%S).sql

# Backup Plane database
docker exec postgres-plane pg_dumpall -U postgres > \
  backups/plane_$(date +%Y%m%d_%H%M%S).sql

# Backup Neo4j
docker exec ai-neo4j neo4j-admin database dump neo4j \
  --to-path=/backups/neo4j_$(date +%Y%m%d_%H%M%S).dump
```

### **6.2 Backup Archon Database (Supabase Cloud)**

```bash
# Via Supabase Dashboard:
# Settings → Database → Backups → Manual Backup

# Ou via CLI (se Supabase CLI instalado):
supabase db dump -f backups/archon_$(date +%Y%m%d_%H%M%S).sql
```

---

## **7. Troubleshooting Database Issues**

### **Problema: Supabase-db não inicia**
```bash
# Ver logs
docker compose logs supabase-db

# Verificar permissões dos volumes
sudo chown -R $USER:$USER ./volumes/supabase_db_data

# Recriar volume
docker compose down -v
docker compose up -d supabase-db
```

### **Problema: Plane não conecta ao postgres-plane**
```bash
# Verificar se postgres-plane está rodando
docker compose ps postgres-plane

# Testar conexão
docker exec postgres-plane pg_isready -U postgres

# Ver configuração do Plane
docker compose logs plane-api | grep -i database
```

### **Problema: Archon não conecta ao Supabase Cloud**
```bash
# Verificar variáveis de ambiente
docker compose -f ~/ai-stack/Archon/docker-compose.yml exec archon-server env | grep SUPABASE

# Testar conectividade
docker compose -f ~/ai-stack/Archon/docker-compose.yml exec archon-server \
  curl -v https://seu-projeto.supabase.co

# Ver logs de erro
docker compose -f ~/ai-stack/Archon/docker-compose.yml logs archon-server | tail -50
```

---

**📝 Documentação Relacionada:**
- [CLAUDE.md](../CLAUDE.md) - Comandos de gerenciamento de banco de dados
- [ARCHON_INTEGRATION.md](../docs/ARCHON_INTEGRATION.md) - Setup completo do Archon
- [ARCHON_VALIDATION.md](../docs/ARCHON_VALIDATION.md) - Scripts de validação

**📅 Última Atualização:** 2025-01-28
