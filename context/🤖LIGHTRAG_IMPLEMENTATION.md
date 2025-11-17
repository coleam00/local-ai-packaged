# **🤖 Implementação do LightRAG**

> **📚 Documentação de Referência:**
> - [CLAUDE.md](../CLAUDE.md) - Comandos de gerenciamento do LightRAG
> - [🔧ARCHITECTURE.md](🔧ARCHITECTURE.md) - Arquitetura completa do sistema
> - [🗄️DATABASE_SETUP.md](🗄️DATABASE_SETUP.md) - Schema RAG e configurações de banco

Este documento foca na configuração e utilização do `LightRAG`, o núcleo do nosso sistema de Retrieval-Augmented Generation.

## **1. Vantagens do LightRAG**

LightRAG foi escolhido por sua abordagem híbrida que supera as limitações do RAG tradicional e os altos custos do GraphRAG.

*   **Híbrido:** Combina busca vetorial (para precisão semântica) com grafos de conhecimento (para entendimento contextual).
*   **Eficiente:** Permite a adição incremental de dados sem reconstruir todo o grafo, resultando em uma redução de até 85% nas chamadas de API em comparação com o GraphRAG.
*   **Multimodal:** Através da integração com `RAG-Anything`, pode processar PDFs, documentos do Office e imagens, extraindo texto, legendas e estruturas de tabelas.

## **2. Configuração no Ecossistema `ai-stack`**

O LightRAG é executado como o serviço `ai-lightrag` no `docker-compose.yml`. Suas configurações são gerenciadas principalmente através do arquivo `.env.lightrag.env`.

### **2.1. Arquitetura de Storage Dual (PostgreSQL + Neo4j)**

O LightRAG implementa uma **estratégia de armazenamento híbrido** que combina o melhor de dois mundos:

| Componente | Storage Backend | Porta | Função |
|------------|----------------|-------|--------|
| **Vector Storage** | PostgreSQL + pgvector (supabase-db) | 5432 | Busca semântica de similaridade em chunks |
| **Graph Storage** | Neo4j | 7687 (Bolt) | Travessia de relacionamentos e contexto global |
| **KV Storage** | PostgreSQL (supabase-db) | 5432 | Metadados, hashes, status de documentos |
| **Doc Status** | PostgreSQL (supabase-db) | 5432 | Tracking de processamento (PENDING, COMPLETED, ERROR) |

**Por que híbrido?**
- ✅ **PostgreSQL**: ACID guarantees, full-text search, embeddings via pgvector
- ✅ **Neo4j**: Superior para travessia de grafos, entidades e relacionamentos complexos
- ✅ **Juntos**: Recuperação local (vetores) + global (grafo) = máximo contexto

### **2.2. Conexão com o Banco de Dados**

A configuração crítica é garantir que o LightRAG se conecte corretamente ao contêiner `supabase-db` (**NÃO** postgres-plane, que é exclusivo do Plane).

**Trecho de `.env.lightrag.env`:**
```ini
# --- Configuração dos Tipos de Storage ---
LIGHTRAG_KV_STORAGE=PGKVStorage
LIGHTRAG_DOC_STATUS_STORAGE=PGDocStatusStorage
LIGHTRAG_GRAPH_STORAGE=Neo4JStorage # Usa Neo4j para o grafo
LIGHTRAG_VECTOR_STORAGE=PGVectorStorage # Usa PostgreSQL para vetores

# --- Configuração do PostgreSQL (apontando para Supabase) ---
POSTGRES_HOST=supabase-db
POSTGRES_PORT=5432
POSTGRES_USER=supabase_admin # Usuário correto com permissões
POSTGRES_PASSWORD=${DB_PASSWORD} # Herda do .env principal
POSTGRES_DATABASE=postgres

# --- Configuração do Neo4j ---
NEO4J_URI=neo4j://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=${NEO4J_PASSWORD}
```

### **2.3. Integração com LiteLLM Proxy (Host Machine)**

O LightRAG **nunca** chama os provedores de LLM diretamente. Em vez disso, ele aponta para o **LiteLLM Proxy** rodando no **host** (porta 4000), que centraliza e gerencia todas as chamadas.

**Arquitetura de Comunicação:**
```
┌──────────────────┐
│  LightRAG        │
│  (Docker:9621)   │
└────────┬─────────┘
         │ http://host.docker.internal:4000
         ▼
┌──────────────────────────────────┐
│  LiteLLM Proxy (Host:4000)       │
│  Router Universal de LLMs        │
└────────┬─────────────────────────┘
         │
    ┌────┴────────┬──────────┐
    ▼             ▼          ▼
┌────────┐  ┌─────────┐  ┌──────────┐
│OpenAI  │  │Anthropic│  │GitHub    │
│API     │  │Claude   │  │Copilot   │
└────────┘  └─────────┘  └──────────┘
```

**Trecho de `.env.lightrag.env`:**
```ini
# --- Configuração do LLM (apontando para LiteLLM Proxy no HOST) ---
LLM_BINDING=openai # LiteLLM expõe uma API compatível com OpenAI
LLM_MODEL=claude-3.5-sonnet-generate # Nome do modelo definido no config do LiteLLM
LLM_BINDING_HOST=http://host.docker.internal:4000  # Acessa host via Docker
LLM_BINDING_API_KEY=${LITELLM_MASTER_KEY}

# --- Configuração de Embedding (também via LiteLLM) ---
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=openai-embedding-large
EMBEDDING_DIM=1536
EMBEDDING_BINDING_HOST=http://host.docker.internal:4000  # Mesma ponte
EMBEDDING_BINDING_API_KEY=${LITELLM_MASTER_KEY}
```

**Por que LiteLLM no host (não Docker)?**
- ✅ Simplifica roteamento de rede (localhost:4000)
- ✅ Facilita debugging durante desenvolvimento
- ✅ Acesso direto a credenciais do GitHub Copilot
- ✅ Sem complexidade de networking Docker
- ✅ Compartilhado entre ai-stack e Archon (se usado)

## **3. Pipeline de Processamento (RAG-Anything)**

O fluxo de trabalho de ingestão, orquestrado pelo `n8n`, utiliza o pipeline do RAG-Anything:

```
Documento → Parse → Categorize → Analyze → Index
```

1.  **Parse:** Um documento (ex: PDF) é decomposto em seus componentes: texto, imagens, tabelas.
2.  **Categorize:** Cada componente é roteado para um analisador especializado.
3.  **Analyze:**
    *   **Texto:** Extração de entidades e relacionamentos.
    *   **Imagens:** Geração de legendas descritivas via modelo de visão (GPT-4o).
    *   **Tabelas:** Interpretação da estrutura e resumo em linguagem natural.
4.  **Index:** Todo o conteúdo enriquecido é vetorizado e armazenado: chunks no `supabase-db` (PostgreSQL) e o grafo de conhecimento no `ai-neo4j`.

---

## **4. Modos de Recuperação do LightRAG**

O LightRAG oferece **4 modos** de recuperação, cada um com trade-offs de performance e qualidade:

| Modo | Descrição | Quando Usar |
|------|-----------|-------------|
| **naive** | Busca vetorial simples sem grafo | Queries rápidas, contexto local suficiente |
| **local** | Busca vetorial + entidades locais | Precisão maior, ainda performático |
| **global** | Travessia de grafo global | Contexto amplo, múltiplos documentos |
| **hybrid** | Combina local + global | **Recomendado para produção** (máximo contexto) |

**Exemplo de query via API:**
```bash
curl -X POST http://localhost:9621/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LIGHTRAG_API_KEY}" \
  -d '{
    "query": "Como implementar autenticação no projeto?",
    "search_type": "hybrid",
    "limit": 5
  }'
```

---

## **5. Comandos Úteis para LightRAG**

### **5.1. Verificar Saúde do Serviço**
```bash
# Health check
curl http://localhost:9621/health

# Ver logs
docker compose logs -f ai-lightrag

# Verificar conectividade com bancos
docker exec ai-lightrag curl http://supabase-db:5432  # PostgreSQL
docker exec ai-lightrag curl http://ai-neo4j:7474     # Neo4j
```

### **5.2. Ingestão de Documentos**
```bash
# Upload de arquivo
curl -X POST http://localhost:9621/documents/file \
  -H "Authorization: Bearer ${LIGHTRAG_API_KEY}" \
  -F "file=@/path/to/document.pdf" \
  -F "metadata={\"source\":\"manual_upload\",\"project\":\"ai-stack\"}"

# Upload de texto direto
curl -X POST http://localhost:9621/documents/text \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LIGHTRAG_API_KEY}" \
  -d '{
    "content": "O LightRAG é um sistema RAG híbrido...",
    "metadata": {"source": "direct_input"}
  }'
```

### **5.3. Verificar Dados no PostgreSQL**
```bash
# Conectar ao banco
docker exec -it supabase-db psql -U supabase_admin -d postgres

# Verificar chunks indexados
SELECT COUNT(*) FROM rag.chunks;

# Ver documentos processados
SELECT id, file_name, file_type, created_at FROM rag.documents ORDER BY created_at DESC LIMIT 10;

# Verificar embeddings
SELECT COUNT(*), COUNT(embedding) as with_embeddings FROM rag.chunks;
```

### **5.4. Verificar Dados no Neo4j**
```bash
# Acessar Neo4j Browser: http://localhost:7474
# Ou via CLI:
docker exec ai-neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
  "MATCH (n) RETURN count(n) as node_count"

# Ver entidades
docker exec ai-neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
  "MATCH (e:Entity) RETURN e.name, labels(e) LIMIT 10"

# Ver relacionamentos
docker exec ai-neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
  "MATCH ()-[r]->() RETURN type(r), count(*) GROUP BY type(r)"
```

---

## **6. Troubleshooting Comum**

### **Problema: LightRAG não conecta ao PostgreSQL**
```bash
# Verificar se supabase-db está rodando
docker compose ps supabase-db

# Testar conexão
docker exec ai-lightrag curl http://supabase-db:5432

# Ver logs de erro
docker compose logs ai-lightrag | grep -i "postgres\|database"

# Verificar variáveis de ambiente
docker exec ai-lightrag env | grep POSTGRES
```

### **Problema: Embeddings não são gerados**
```bash
# Verificar se LiteLLM está rodando no host
ps aux | grep litellm

# Testar LiteLLM do container
docker exec ai-lightrag curl http://host.docker.internal:4000/health

# Testar endpoint de embeddings
curl -X POST http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer sk-auto-headers-2025" \
  -H "Content-Type: application/json" \
  -d '{"model":"text-embedding-3-small","input":["test"]}'
```

### **Problema: Neo4j não está acessível**
```bash
# Verificar se Neo4j está rodando
docker compose ps ai-neo4j

# Testar conexão Bolt
docker exec ai-neo4j neo4j-admin dbms status

# Ver logs
docker compose logs ai-neo4j | tail -50

# Reiniciar Neo4j
docker compose restart ai-neo4j
```

---

**📝 Documentação Relacionada:**
- [CLAUDE.md](../CLAUDE.md) - Comandos completos de desenvolvimento
- [🔧ARCHITECTURE.md](🔧ARCHITECTURE.md) - Arquitetura detalhada do sistema
- [⚙️SYSTEM_WORKFLOWS.md](⚙️SYSTEM_WORKFLOWS.md) - Workflows de ingestão via n8n

**📅 Última Atualização:** 2025-01-28