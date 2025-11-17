# 🚀 ARQUITETURA ESTRATÉGICA: ai-stack RAG + n8n + LiteLLM + MCP

## 📋 VISÃO GERAL DO PROJETO

Você está construindo um **sistema de IA modular e produção-grade** que integra:

1. **LiteLLM** (porta 4001) - Router de LLMs com 33+ modelos
2. **n8n** (porta 5678) - Orquestração de workflows visuais
3. **OpenWebUI** (porta 3001) - Interface cliente para usuários finais
4. **LightRAG** (porta 9621) - Engine de RAG avançado
5. **Neo4j** (porta 7474) - Banco de dados gráfico
6. **Supabase+pgVector** (porta 5432) - Vetores e dados estruturados
7. **Claude Code + MCP** - Interface de desenvolvimento programático

### Fluxo de Dados Proposto

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENTE FINAL                          │
│  (OpenWebUI, Claude Code, ou qualquer MCP client)              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        n8n WORKFLOWS                            │
│  (Orquestração, transformação, validação de dados)              │
│                                                                 │
│  - Ingestão de documentos                                       │
│  - Chunking e preprocessing                                     │
│  - Enriquecimento com metadados                                 │
│  - Gerenciamento de tasks                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
        ┌──────────────────┐  ┌──────────────────┐
        │   LightRAG API   │  │  LiteLLM Proxy   │
        │   (9621)         │  │   (4001)         │
        └────────┬─────────┘  └─────────┬────────┘
                 │                      │
        ┌────────┴──────────────────────┴────────┐
        │                                        │
        ▼                                        ▼
    ┌──────────────┐                    ┌──────────────┐
    │  Neo4j KG    │                    │  OpenAI,     │
    │  (7474)      │                    │  Anthropic,  │
    │              │                    │  Google      │
    │  Graphs &    │                    │              │
    │  Relations   │                    │  33+ models  │
    └──────────────┘                    └──────────────┘
        │
        ▼
    ┌──────────────┐
    │ Supabase     │
    │ + pgVector   │
    │ (5432)       │
    │              │
    │ Embeddings   │
    │ & Metadata   │
    └──────────────┘
```

---

## 🎯 ESTRATÉGIA RAG MULTICAMADAS

### Camada 1: Ingestão (n8n Workflow)

**Responsabilidade:** Receber documentos e preparar para processamento

```yaml
Workflow: "RAG_Ingestão"
Triggers:
  - OpenWebUI (via HTTP)
  - MCP Client (Claude Code)
  - N8N HTTP Endpoint
  
Steps:
  1. Receber documento (PDF, TXT, URL)
  2. Validar formato e tamanho
  3. Extrair conteúdo (OCR se PDF)
  4. Dividir em chunks (128-512 tokens)
  5. Adicionar metadados (source, date, tags)
  6. Enviar para LightRAG
```

### Camada 2: Processamento (LightRAG)

**Responsabilidade:** RAG inteligente com múltiplas estratégias

**3 Estratégias Paralelas:**

#### A. **Semantic Search** (Vectorial)
- Embeddings via LiteLLM (text-embedding-3-small)
- Armazenamento em Supabase pgVector
- Busca por similaridade semântica
- **Melhor para:** Conceitos e temas relacionados

#### B. **Knowledge Graph** (Neo4j + Graphiti)
- Extração automática de entidades (pessoas, orgs, conceitos)
- Extração de relacionamentos (has_knowledge, belongs_to, related_to)
- Armazenamento em Neo4j
- Busca por caminho gráfico (path traversal)
- **Melhor para:** Contexto relacional complexo

#### C. **BM25 Search** (Full-text)
- Indexação full-text built-in no Graphiti
- Busca por keywords específicas
- **Melhor para:** Busca exata e específica

### Camada 3: Geração (LiteLLM)

**Responsabilidade:** Generar respostas contextualmente relevantes

```
Prompt Structure:
┌─────────────────────────────────────────────┐
│ SYSTEM PROMPT                               │
│ - Papel da IA                               │
│ - Instruções de tom e estilo                │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│ CONTEXTO RECUPERADO (RAG)                   │
│                                             │
│ [Semantic Results]                          │
│ "Based on document X: ..."                  │
│                                             │
│ [Graph Results]                             │
│ "Related entities: ..."                     │
│                                             │
│ [BM25 Results]                              │
│ "Exact matches: ..."                        │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│ USER QUERY                                  │
│ "Qual é a relação entre X e Y?"             │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│ LiteLLM → Melhor Modelo Disponível          │
│ (gpt-4o, claude-3.5-sonnet, gemini-2.0)     │
│                                             │
│ Gera resposta sintetizada                   │
└─────────────────────────────────────────────┘
```

---

## 🛠️ COMPARAÇÃO: Graphiti vs GraphRAG vs Neo4j Vanilla

### Graphiti (RECOMENDADO para seu caso)

| Aspecto | Graphiti |
|---------|----------|
| **Tipo** | Framework de Knowledge Graph dinâmico |
| **Atualização** | Real-time incremental ✅ |
| **Busca** | Híbrida (semantic + BM25 + graph) ✅ |
| **Temporal** | Bi-temporal (evento vs ingestão) ✅ |
| **Neo4j Required?** | Sim (roda sobre Neo4j) |
| **MCP Server** | Integração nativa ✅ |
| **Latência** | Sub-segundo |
| **Customização** | Entidades custom via Pydantic |
| **Melhor para** | Dados dinâmicos e relacionamentos complexos |

### GraphRAG (Microsoft)

| Aspecto | GraphRAG |
|---------|----------|
| **Tipo** | Batch-oriented document summarization |
| **Atualização** | Reprocessamento completo ❌ |
| **Busca** | Comunidades + LLM summarization |
| **Temporal** | Básico |
| **Latência** | Segundos a minutos |
| **Melhor para** | Documentos estáticos e grandes volumes |

### Neo4j Vanilla

| Aspecto | Neo4j |
|---------|-------|
| **Tipo** | Database de grafo |
| **Query** | Cypher (SQL-like) |
| **Busca** | Apenas graph traversal |
| **Você constrói** | Toda a lógica de RAG |
| **Melhor para** | Dados estruturados e queries complexas |

**Recomendação:** Use **Graphiti** + **Neo4j** + **Supabase**

---

## 🔌 APIS LITELLM PARA INGESTÃO RAG

### 1. Chat Completions (Sua API principal)

```bash
# Endpoint
POST /v1/chat/completions

# Request
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "system",
      "content": "Você é um especialista em extração de conhecimento..."
    },
    {
      "role": "user",
      "content": "Extraia as entidades do texto: ..."
    }
  ],
  "temperature": 0.7,
  "max_tokens": 2000
}

# Response
{
  "choices": [{
    "message": {
      "content": "Entidades encontradas: ..."
    }
  }],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 450
  }
}
```

### 2. Embeddings (Para vetorização)

```bash
# Endpoint
POST /v1/embeddings

# Request
{
  "model": "text-embedding-3-small",
  "input": ["Primeiro chunk de texto...", "Segundo chunk..."],
  "encoding_format": "float"
}

# Response
{
  "data": [
    {"embedding": [0.123, 0.456, ...], "index": 0},
    {"embedding": [0.789, 0.012, ...], "index": 1}
  ],
  "usage": {
    "prompt_tokens": 50,
    "total_tokens": 50
  }
}
```

### 3. Batch Processing (Para volumes grandes)

```bash
# Para ingerir 10.000 documentos em paralelo
POST /v1/chat/completions (com retry logic)

Usar concorrência com semaPhore:
- SEMAPHORE_LIMIT=50 (aumentar conforme sua rate limit)
```

### 4. Token Counting

```bash
# Verificar custos antes de processar
POST /v1/completions/token/count

{
  "messages": [...],
  "model": "gpt-4o"
}
```

---

## 🔄 FLUXO COMPLETO: OpenWebUI → n8n → LightRAG → LiteLLM

### Step-by-Step

#### 1. Usuário envia query no OpenWebUI

```
Usuário: "Qual foi o impacto da lei X no setor Y?"
│
├─→ OpenWebUI registra a conversa em Supabase
│
└─→ HTTP POST para n8n webhook
```

#### 2. n8n recebe e processa

```yaml
n8n Workflow "RAG_Query_Handler":
  
  Step 1: Receber Query
    input: "Qual foi o impacto..."
  
  Step 2: Pré-processamento
    - Tokenizar query
    - Remover stopwords
    - Expandir com sinônimos
  
  Step 3: Parallelizar 3 buscas
    
    Ramo A: Semantic Search
      - Embeddar query via LiteLLM
      - Buscar em Supabase pgVector
      - Top-5 resultados semânticos
    
    Ramo B: Graph Search
      - Enviar query para Neo4j
      - Buscar por entidades "lei X" e "setor Y"
      - Recuperar 10 hops de distância
    
    Ramo C: Full-text Search
      - Buscar keywords em LightRAG
      - Top-10 matches por relevância
  
  Step 4: Consolidar contexto
    - Mesclar top-3 de cada ramo
    - Ordenar por relevância
    - Limitar a 4K tokens
  
  Step 5: Chamar LiteLLM
    - Montar prompt final
    - Usar melhor modelo (gpt-4o)
    - Stream response
  
  Step 6: Retornar para OpenWebUI
    - Incluir fontes
    - Incluir confidence scores
    - Salvar para histórico
```

#### 3. LightRAG processa embedding

```python
# Pseudocódigo
graphiti = Graphiti(
    graph_driver=Neo4jDriver(...),
    llm_client=OpenAIClient(config),
    embedder=OpenAIEmbedder(...)
)

# Ingerir documento
await graphiti.add_episodes(
    episodes=[{
        "content": "Lei X estabeleceu...",
        "source": "openwebui_user_123",
        "metadata": {"type": "user_query", "timestamp": "..."}
    }],
    **metadata
)

# Buscar contexto
results = await graphiti.search_relationships(
    query="impacto da lei X",
    limit=10,
    search_type="hybrid"  # semantic + keyword + graph
)
```

#### 4. LiteLLM gera resposta

```python
from litellm import completion

response = completion(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": "Você é um especialista em análise de legislação..."
        },
        {
            "role": "user",
            "content": f"""
            Contexto de pesquisa:
            {consolidado_do_rag}
            
            Pergunta: Qual foi o impacto da lei X no setor Y?
            
            Responda em português, citando as fontes.
            """
        }
    ],
    temperature=0.7,
    max_tokens=2000,
    stream=True
)

# Stream a resposta de volta pro OpenWebUI
for chunk in response:
    enviar_para_openwebui(chunk)
```

---

## 🎨 INTERFACE n8n + UI MELHORADA

### Opções de UI:

#### 1. **n8n Built-in** (Mais simples)
- Use templates do n8n
- Custom HTML nodes
- Webhooks para renderizar UI externa

#### 2. **SuperDesign + n8n** (Recomendado)
- Criar UI em Figma → SuperDesign
- Exportar como componentes React
- Integrar com n8n HTTP Node
- Dashboard para workflows

#### 3. **Next.js + n8n** (Mais flexível)
- Frontend React/Next.js separado
- Chamar n8n workflows via API
- UI totalmente customizada

### Exemplo: Dashboard do RAG em Next.js

```typescript
// components/RAGDashboard.tsx
export function RAGDashboard() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (q: string) => {
    setLoading(true);
    
    // Chamar n8n webhook
    const response = await fetch("/api/n8n/rag-query", {
      method: "POST",
      body: JSON.stringify({
        query: q,
        userId: user.id,
        timestamp: Date.now()
      })
    });

    // LiteLLM streaming response
    const reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const text = new TextDecoder().decode(value);
      setResults(prev => [...prev, text]);
    }
    
    setLoading(false);
  };

  return (
    <div className="rag-dashboard">
      <SearchInput onSearch={handleSearch} />
      <ResultsPanel results={results} loading={loading} />
      <KnowledgeGraphVisualization />
    </div>
  );
}
```

---

## 🔗 INTEGRAÇÃO: OpenWebUI ↔ n8n ↔ LightRAG

### 1. Registrar Webhook no OpenWebUI

```bash
# Em OpenWebUI Settings
Webhooks > Add
- Name: n8n RAG Handler
- URL: http://localhost:5678/webhook/rag-process
- Events: message.created, document.uploaded
- Auth: Bearer {N8N_WEBHOOK_SECRET}
```

### 2. n8n Webhook Receiver

```yaml
Trigger: Webhook
- Method: POST
- Path: /webhook/rag-process
- Accept: application/json

Body:
{
  "event": "message.created",
  "message": {...},
  "userId": "...",
  "conversationId": "..."
}
```

### 3. Salvar no LightRAG

```python
# n8n Python node (se usar)
import requests

data = {
    "content": body["message"]["content"],
    "source": f"openwebui_{body['userId']}",
    "metadata": {
        "conversation_id": body["conversationId"],
        "timestamp": time.time(),
        "model": body.get("model"),
        "tokens": count_tokens(body["message"]["content"])
    }
}

# Ingerir no LightRAG
response = requests.post(
    "http://localhost:9621/api/episodes",
    json=data,
    headers={"Authorization": f"Bearer {LIGHTRAG_API_KEY}"}
)
```

---

## 🧠 MCP PARA LIGHTRAG (FastMCP)

### Criar MCP Server para LightRAG

```python
# lightrag_mcp_server.py
from fastmcp import Server
from pydantic import BaseModel

server = Server("lightrag-mcp")

class SearchQuery(BaseModel):
    query: str
    search_type: str = "hybrid"
    limit: int = 5

@server.tool()
async def search_rag(query: SearchQuery) -> dict:
    """Search the LightRAG knowledge base"""
    graphiti = get_graphiti_instance()
    results = await graphiti.search_relationships(
        query=query.query,
        limit=query.limit,
        search_type=query.search_type
    )
    return {
        "results": results,
        "count": len(results)
    }

@server.tool()
async def add_to_rag(content: str, metadata: dict) -> dict:
    """Add content to LightRAG"""
    graphiti = get_graphiti_instance()
    episode = await graphiti.add_episodes(
        episodes=[{
            "content": content,
            "metadata": metadata
        }]
    )
    return {"status": "ingested", "episode_id": episode.id}

@server.resource("rag://knowledge-graph")
async def get_graph_stats() -> dict:
    """Get statistics about the knowledge graph"""
    graphiti = get_graphiti_instance()
    stats = await graphiti.get_graph_stats()
    return stats

if __name__ == "__main__":
    server.run()
```

### Usar no Claude Code

```
# .mcp.json
{
  "mcpServers": {
    "lightrag": {
      "command": "python",
      "args": ["lightrag_mcp_server.py"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "OPENAI_API_KEY": "..."
      }
    }
  }
}
```

### Agora Claude pode fazer:

Claude Code:
Use o MCP do LightRAG para buscar informações sobre a arquitetura de microserviços

Claude vai:
1. Chamar `search_rag` com query "arquitetura de microserviços"
2. Receber resultados do Neo4j + pgVector
3. Usar no contexto da sua análise
4. Adicionar insights com `add_to_rag`

---

## 🎯 MODULARIZAÇÃO: Extrair Plane → n8n

### Workflow no n8n para Task Management

```yaml
Workflow: "Plane_TaskManager"

Triggers:
  - n8n HTTP
  - Schedule (cron)
  - Manual trigger

Steps:
  1. Listar tarefas de uma projeto/espaço
  2. Associar com chunks de RAG
  3. Atualizar status baseado em progresso
  4. Criar relacionamentos no Neo4j
  5. Notificar via webhook

Example:
  trigger: "Document ingestão concluída"
  -> create_task("Review document X")
  -> tag_with("rag_processed", "pending_review")
  -> notify_team("New RAG document ready for review")
```

---

## 📊 STACK FINAL RECOMENDADO

### Tecnologias por Camada

| Camada | Componente | Tecnologia | Porta | Responsabilidade |
|--------|-----------|------------|-------|-----------------|
| **UI** | Cliente | OpenWebUI | 3001 | Interface usuário |
| **Cliente** | IDE | Claude Code | MCP | Desenvolvimento |
| **Orchestração** | Workflows | n8n | 5678 | Automação |
| **LLM** | Router | LiteLLM | 4001 | Roteamento de modelos |
| **RAG** | Engine | LightRAG | 9621 | Busca contextual |
| **Dados** | Grafo | Neo4j | 7474 | Conhecimento estruturado |
| **Dados** | Vetores | Supabase pgVector | 5432 | Embeddings |
| **Desenvolvimento** | MCP** | FastMCP | Custom | Integração programática |

---

## 🚀 PRÓXIMOS PASSOS

1. **Implementar Graphiti MCP Server** (Prioridade 1)
   - Criar FastMCP server para LightRAG
   - Testar com Claude Code

2. **Criar n8n Workflows** (Prioridade 2)
   - RAG Ingestão
   - RAG Query Handler
   - Plane Task Manager

3. **Integrar OpenWebUI → n8n** (Prioridade 3)
   - Webhooks
   - Autenticação
   - Streaming responses

4. **UI Melhorada** (Prioridade 4)
   - Dashboard em Next.js
   - Visualização Neo4j
   - Componentes Figma

5. **Adicionar Outras Estratégias RAG** (Prioridade 5)
   - Reranking com cross-encoders
   - Recursive retrieval
   - Hypothetical Document Embeddings

---

## ✅ CHECKLIST IMPLEMENTAÇÃO

```
[ ] LiteLLM rodando com /v1/embeddings
[ ] Supabase pgVector configurado
[ ] Neo4j acessível e populado
[ ] Graphiti instalado e testado
[ ] n8n webhook receiver pronto
[ ] OpenWebUI conectado a n8n
[ ] MCP Server LightRAG criado
[ ] Claude Code integrado com MCP
[ ] Dashboard Next.js basic
[ ] Documentação completa
```

---

Pronto para começar? Qual camada quer implementar primeiro? 🚀