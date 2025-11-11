## 🚀 Ultimate n8n Agentic RAG Template

**Author:** [Cole Medin](https://www.youtube.com/@ColeMedin)

NOTE: This n8n RAG template works for self-hosted n8n and requires you to install the [community MCP node](https://www.npmjs.com/package/n8n-nodes-mcp).

## What is this?
This template provides a complete implementation of an **Agentic RAG (Retrieval Augmented Generation)** system in n8n that can be extended easily for your specific use case and knowledge base. Unlike standard RAG which only performs simple lookups, this agent can reason about your knowledge base, self-improve retrieval, and dynamically switch between different tools based on the specific question. 

This powerful agent combines traditional vector-based retrieval from a Postgres database (using PGVector) with the deep relational query capabilities of a Knowledge Graph (powered by Graphiti and Neo4j). This hybrid approach allows the agent to not only find relevant information but also understand and navigate the complex relationships between them.

## 🧠 The Power of Knowledge Graphs
Traditional RAG using vector databases is excellent for semantic search, but it struggles to capture the explicit relationships between different entities in your data. When you simply chunk documents and store them in a vector database, it's difficult for an agent to connect the dots between related concepts, people, or products mentioned across different chunks.

This is where knowledge graphs shine. By representing your data as a network of entities and their relationships (e.g., "Company A" *employs* "Person X" who *works on* "Project Y"), we give the agent a structured map of your knowledge. This allows it to answer complex, multi-hop questions that a simple vector search would miss, such as "How do two companies work together?" or "Who is the executive leadership team at a specific company?".

In this template, the RAG pipeline builds the knowledge graph and the vector database simultaneously, giving your agent the best of both worlds.

## Why Agentic RAG?
Standard RAG has significant limitations. An Agentic approach, especially one supercharged with a knowledge graph, overcomes these by:
- **Going beyond simple search:** Instead of just retrieving documents, the agent can reason about the data and decide which tool is best for the job.
- **Connecting the dots:** It can traverse a knowledge graph to uncover hidden relationships across your entire knowledge base, providing deeper insights.
- **Analyzing structured data:** It can query tabular data using SQL for precise numerical analysis, something vector search is not good at.
- **Dynamic tool use:** The agent isn't limited to one method. It dynamically chooses between vector search, SQL queries, knowledge graph traversal, or full document retrieval based on the user's question.

## What makes this template powerful:
- **Intelligent Tool Selection**: The agent intelligently switches between vector RAG lookups, SQL queries for tabular data, and knowledge graph searches for relational questions.
- **Deep Relationship Analysis**: Leverages a Neo4j knowledge graph to uncover and query complex relationships between entities that are impossible to find with vector search alone.
- **Complete Document Context**: Accesses entire documents when needed instead of just isolated chunks.
- **Accurate Numerical Analysis**: Uses SQL for precise calculations on spreadsheet/tabular data.
- **Cross-Document Insights**: Connects information across your entire knowledge base using both vector search and the knowledge graph.
- **Multi-File Processing**: Handles multiple documents in a single workflow loop.
- **Efficient Storage**: Uses JSONB in Postgres to store tabular data without creating new tables for each CSV.

## Getting Started
This template requires a self-hosted n8n instance to run the necessary community nodes and services.

1.  **Set up your environment:**
    *   A self-hosted n8n instance is required.
    *   Set up Graffiti and Neo4j using Docker Compose to run alongside your n8n instance. This will power the knowledge graph.
    *   Install the [n8n-nodes-mcp](https://www.npmjs.com/package/n8n-nodes-mcp) community node in your n8n instance.
2.  **Configure the workflow:**
    *   Run the table creation nodes first to set up your database tables in Postgres.
    *   Configure your credentials for OpenAI, Google Drive, Postgres, and the MCP client.
3.  **Load your data:**
    *   Upload your documents through Google Drive (or swap out for a different file storage solution).
    *   The agent will process them automatically, chunking text for the vector database and extracting entities and relationships for the knowledge graph.
4.  **Start asking questions:**
    *   You can now ask simple questions that will use vector search, or complex relational questions that will leverage the knowledge graph.

## Customization
This template provides a solid foundation that you can extend by:
- Tuning the system prompt for your specific use case to guide the agent on when to use which tool.
- Adding document metadata like summaries.
- Implementing more advanced RAG techniques.
- Optimizing for larger knowledge bases.
- **Note on performance:** Knowledge graphs can be slower and more expensive than vector databases due to the LLM-based entity extraction. They are best for use cases with highly relational data where the extra query power is needed.

---
# Análise do Template: RAG AI Agent Template V5

## 1. Visão Geral
- **Objetivo**: Template de Agente RAG (Retrieval Augmented Generation) com capacidade de processamento multimodal (documentos, planilhas, PDFs, etc.) e análise de relacionamentos com Grafo de Conhecimento.
- **Arquitetura**: Combina LangChain, PostgreSQL (PGVector/Neon), Google Drive, OpenAI, Cohere, e um Grafo de Conhecimento com Graphiti/Neo4j.
- **Autor**: Cole Medin (YouTube: @ColeMedin)

---

## 2. Componentes Principais

### 2.1. Fluxo de Ingestão de Documentos
- **Gatilhos**: 
  - Monitoramento de pasta do Google Drive (criação/atualização de arquivos)
  - Limpeza automática de arquivos excluídos (a cada 15 minutos)
- **Processamento**:
  - Extração de texto de múltiplos formatos (PDF, Excel, CSV, Google Docs)
  - Divisão inteligente de texto com LLM (chunking semântico)
  - Armazenamento vetorial com PGVector
  - Extração de entidades e relacionamentos para o Grafo de Conhecimento (Graphiti/Neo4j)

### 2.2. Banco de Dados
- **Tabelas**:
  - `document_metadata` (metadados dos arquivos)
  - `document_rows` (dados tabulares em JSONB)
  - `documents_pg` (vetores de documentos)
- **Grafo de Conhecimento**:
  - Neo4j para armazenar nós (entidades) e arestas (relacionamentos).
- **Características**:
  - Schema flexível para dados estruturados/não estruturados e relacionais.
  - Operações UPSERT para atualizações.

### 2.3. Agente RAG Inteligente
- **Ferramentas Disponíveis**:
  - Busca vetorial (RAG tradicional)
  - Consulta SQL em dados tabulares
  - Acesso ao conteúdo completo de documentos
  - Busca em grafo de conhecimento (MCP/Neo4j) para análise de relacionamentos.
- **Lógica de Decisão**:
  - Seleção automática da melhor ferramenta baseada na pergunta (e.g., busca vetorial para perguntas simples, grafo para perguntas relacionais).
  - Fallback entre estratégias de recuperação.

---

## 3. Fluxos de Trabalho Específicos

### 3.1. Processamento de Novos Documentos

Google Drive → Metadados → Extração →
├→ Texto: Chunking → Vetorização → PGVector
├→ Tabelas: JSONB → document_rows
└→ Grafo: Extração de Entidades/Relacionamentos → MCP Client → Knowledge Graph (Neo4j)

### 3.2. Interface de Chat
Webhook → Agente RAG →
├→ Ferramentas: [RAG, SQL, Documentos, Grafo]
└→ Memória: PostgreSQL Chat History


### 3.3. Manutenção Automática
- Limpeza de arquivos excluídos do Google Drive
- Remoção correspondente nos vetores e metadados
- Agendamento a cada 15 minutos

---

## 4. Integrações e Credenciais

### 4.1. Serviços Externos
- **OpenAI**: GPT-4.1 & Embeddings
- **Cohere**: Reranker para melhorar relevância
- **Google Drive**: Armazenamento e triggers
- **PostgreSQL**: Neon Tech (PGVector + dados relacionais)
- **MCP Client (Graphiti/Neo4j)**: Para extração e busca no grafo de conhecimento.

### 4.2. Credenciais Configuradas
- `OpenAi account` (GPT + embeddings)
- `Google Drive account` (OAuth2)
- `RAG Neon` (PostgreSQL)
- `CohereApi account` (reranking)
- `MCP Client (SSE) account` (knowledge graph)

---

## 5. Características Técnicas Avançadas

### 5.1. Chunking Inteligente
- Usa LLM para identificar pontos de quebra semânticos
- Tamanho dinâmico (400-1000 caracteres)
- Preserva contexto entre chunks

### 5.2. RAG Híbrido
- Combina: Busca vetorial + Re-ranqueamento + Grafo de Conhecimento para uma compreensão mais profunda.
- Fallback entre diferentes estratégias.

### 5.3. Processamento Multimodal
- **Documentos**: PDF, Google Docs, texto
- **Planilhas**: Excel, Google Sheets, CSV
- **Dados Tabulares**: Análise via SQL + agregações
- **Dados Relacionais**: Análise via Grafo de Conhecimento

---

## 6. Instruções de Uso

### 6.1. Configuração Inicial
1.  **Ambiente**: Requer n8n auto-hospedado, Docker, Graffiti e Neo4j.
2.  **Instalação**: Instale o nó comunitário `n8n-nodes-mcp`.
3.  **Banco de Dados**: Execute os nós de criação de tabelas no Postgres.
4.  **Credenciais**: Configure as credenciais para todos os serviços.
5.  **Monitoramento**: Defina a pasta do Google Drive para monitoramento.

### 6.2. Operação Normal
- Documentos são processados automaticamente (vetores e grafo).
- Chat disponível via webhook/interface.
- Limpeza automática em background.

---

## 7. Pontos de Destaque

### ✅ Vantagens
- Arquitetura agentica que decide a melhor ferramenta para a tarefa.
- Processamento multimodal e híbrido (vetorial + grafo).
- Sistema auto-gerenciável (limpeza automática).
- Escalável (Neon PostgreSQL + PGVector + Neo4j).

### ⚠️ Complexidades
- Múltiplas dependências de serviços.
- Configuração inicial extensa (requer ambiente auto-hospedado).
- Vários fluxos paralelos.

---

## 8. Possíveis Customizações
- Adição de novos conectores de arquivos
- Implementação de cache de embeddings
- Otimização de prompts para domínios específicos
- Adição de ferramentas especializadas
