# Guia de Operações: Local AI Packaged (Arquitetura RAG V4 - Consolidada)

Este documento é o seu guia central para entender, operar e desenvolver no ecossistema `local-ai-packaged`. Ele foi completamente reescrito para refletir a nova arquitetura consolidada, focada em uma estratégia de RAG (Retrieval-Augmented Generation) avançada, modularidade e uma experiência de desenvolvimento simplificada.

## 1. Visão Geral da Arquitetura

O projeto foi refatorado para uma arquitetura de múltiplos serviços mais limpa e coesa, orquestrada por um `docker-compose.yml` principal.

- **Core RAG (Baseado em `all-rag-strategies`)**: O coração do sistema é a implementação avançada de RAG do diretório `all-rag-strategies`. Ele utiliza um banco de dados **PostgreSQL com a extensão pgvector**, rodando localmente através do stack da **Supabase**.
- **Banco de Dados RAG (Supabase Local)**: A stack da Supabase é usada para gerenciar a instância local do Postgres, que armazena os documentos e embeddings para o sistema RAG. O schema do banco de dados é inicializado automaticamente a partir de `all-rag-strategies/implementation/sql/schema.sql`.
- **Ingestão de Dados (Serviço Dedicado)**: Um novo serviço `ingestion` foi adicionado ao Docker Compose. Ele é responsável por processar documentos do diretório `all-rag-strategies/implementation/documents` e populando o banco de dados RAG.
- **Orquestração e Agente (n8n)**: O **n8n** continua sendo o motor para orquestração do agente RAG. O workflow padrão (`Local_RAG_AI_Agent_n8n_Workflow.json`) foi atualizado para a versão V5, que interage com o banco de dados RAG local.
- **Interface de Chat (Open WebUI)**: A interação do usuário com o agente RAG é feita através do **Open WebUI**, que se conecta ao n8n por meio do script `n8n_pipe.py`.
- **Módulo Archon (Serviço Desacoplado)**: O **Archon** agora funciona como um módulo completamente independente. Ele é iniciado pelo `docker-compose.yml` principal, mas utiliza seu **próprio banco de dados na nuvem Supabase** (configurado no `.env`) e não compartilha o banco de dados com o sistema RAG.

## 2. Configuração do Ambiente (`.env`)

O arquivo `.env.example` na raiz do projeto foi reestruturado para maior clareza. Copie-o para `.env` e preencha as variáveis.

#### Configuração do RAG e Serviços Principais
```env
# --- [required] AI & RAG Configuration ---
OPENAI_API_KEY=your-openai-api-key
LLM_CHOICE=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# --- [required] Supabase Secrets for Local RAG Database ---
POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password
# ... (outras variáveis da Supabase)

# --- Database URL for RAG components ---
# Esta URL é usada pelo serviço de ingestão e pelo CLI do RAG.
DATABASE_URL="postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres"
```

#### Configuração do Módulo Archon
```env
# --- [optional] Archon Configuration ---
# Aponte para o seu projeto Supabase na nuvem para o Archon
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_KEY=<your-supabase-service-key>
LLM_BASE_URL=http://host.docker.internal:4000/v1
```

## 3. Como Executar o Projeto

O script `start_services.py` foi simplificado e agora gerencia toda a stack com um único fluxo.

```bash
# Iniciar todos os serviços (com perfil de CPU, por padrão)
python start_services.py

# Iniciar com um perfil de GPU específico
python start_services.py --profile gpu-nvidia

# Parar todos os serviços
docker compose -p localai down

# PARAR E DESTRUIR TODOS OS DADOS (use com cuidado!)
# Isso removerá os volumes do Docker, incluindo o banco de dados RAG.
docker compose -p localai down -v
```

## 4. O Novo Sistema RAG

### 4.1. Ingestão de Dados

A ingestão de dados agora é tratada por um serviço Docker dedicado.

1.  **Adicione Documentos**: Coloque os arquivos que você deseja ingerir no diretório `all-rag-strategies/implementation/documents`.
2.  **Execute o Serviço de Ingestão**: Para iniciar o processo de ingestão, execute o Docker Compose com o perfil `ingestion`.

    ```bash
    # Inicia o serviço de ingestão para processar os documentos
    docker compose --profile ingestion up

    # O serviço irá parar automaticamente após a conclusão.
    # Você pode então derrubá-lo para limpar.
    docker compose --profile ingestion down
    ```

### 4.2. Interação via CLI (Para Desenvolvedores)

O `rag_agent_advanced.py` é uma ferramenta de linha de comando poderosa para interagir diretamente com o sistema RAG, testar diferentes estratégias e depurar.

- **Como Usar**:
  ```bash
  # Certifique-se de que seu .env está configurado e o banco de dados está rodando.
  # Execute o agente a partir da raiz do projeto:
  python -m all-rag-strategies.implementation.rag_agent_advanced
  ```
- **Funcionalidades**: O CLI permite testar estratégias como Re-ranking, Multi-Query RAG e mais, diretamente no seu terminal.

### 4.3. Interação via Interface Gráfica (Open WebUI + n8n)

A interação principal do usuário final acontece através do Open WebUI.

- **Como Funciona**: O `n8n_pipe.py` foi atualizado para apontar para o webhook do novo workflow (`RAG_AI_Agent_Template_V5.json`) que agora é o padrão em `Local_RAG_AI_Agent_n8n_Workflow.json`. Este workflow executa o agente RAG que consulta o banco de dados Supabase/Postgres local.
- **Setup do n8n**:
    1. Acesse o n8n em `http://localhost:5678`.
    2. Configure as credenciais do **PostgreSQL**, apontando para o serviço `db` com as credenciais do seu `.env`.
    3. Configure as credenciais do **OpenAI**.

## 5. Módulo Archon

- **Independência**: O Archon agora é um "vizinho" dos outros serviços, não o centro. Ele é iniciado pelo `docker-compose.yml` principal, mas usa seu próprio `docker-compose.yml` (`Archon/docker-compose.yml`) e se conecta a um banco de dados na nuvem, conforme definido no `.env`.
- **Comunicação**: Ele se comunica com o LiteLLM local para requisições de LLM, o que permite que ele se beneficie do gerenciamento centralizado de modelos.

## 6. Comandos Úteis

```bash
# Ver os logs de todos os contêineres
docker compose -p localai logs -f

# Ver os logs de um serviço específico (ex: n8n, supabase-db)
docker compose -p localai logs -f n8n
docker compose -p localai logs -f neo4j 
docker compose -p localai logs -f supabase-db

# Acessar o banco de dados RAG (Postgres)
# O nome do serviço do banco de dados da Supabase é 'db'
docker compose -p localai exec db psql -U postgres

# Dentro do psql, você pode verificar as tabelas do RAG:
\dt public.*

# E verificar se a extensão pgvector está ativa:
\dx vector
```

## 7. Metodologia de Desenvolvimento: Plano, Implementação e Validação

Para construir software de forma consistente com assistência de IA, adotamos um fluxo de trabalho sistemático baseado no modelo **Plano, Implementação e Validação**. Este modelo estrutura a interação com o assistente de IA para garantir resultados previsíveis e de alta qualidade, integrando ferramentas do nosso ecossistema como o Archon.

### 7.1. Fase 1: Planejamento (Plan)

Esta é a fase mais crítica e envolve fornecer à IA o contexto completo para a tarefa.

1.  **Vibe Planning**: Comece com uma conversa exploratória e de forma livre com o assistente de IA para pesquisar ideias, analisar a arquitetura e o código existente.
2.  **Formalizar Requisitos**: Após a exploração, crie um arquivo (`initial.md` ou similar) que sirva como um Documento de Requisitos do Produto (PRD) de alto nível. Ele deve delinear a funcionalidade, referências e pontos de integração.
3.  **Engenharia de Contexto para um Plano Detalhado**: Converta o PRD de alto nível em um plano de implementação detalhado e acionável. Utilize técnicas como Geração Aumentada por Recuperação (RAG) para alimentar a IA com arquivos de código, documentação e exemplos relevantes, permitindo a criação de um plano passo a passo.

### 7.2. Fase 2: Implementação (Implement)

Esta fase foca na execução controlada e sequencial do plano gerado.

- **Execução Tarefa por Tarefa**: Siga estritamente o plano, concluindo as tarefas granulares uma a uma. Para gerenciar o progresso, utilize uma ferramenta de gerenciamento de tarefas como o **Archon** (descrito na Seção 5) ou uma checklist em markdown. Este processo controlado minimiza erros e "alucinações" da IA.
- **Automação com "Slash Commands"**: Use comandos reutilizáveis (ex: `/primer`, `/create_plan`) para automatizar estágios recorrentes do fluxo de trabalho, como carregamento de contexto e geração de planos.
- **Contexto Primário para Implementação**: Toda a escrita e modificação de código deve ocorrer na janela de contexto primária da IA. Sub-agentes não devem ser usados para implementação, pois suas memórias isoladas podem causar conflitos e sobreposição de alterações.

### 7.3. Fase 3: Validação (Validate)

A validação é um processo de múltiplas camadas para garantir a qualidade do código.

- **Validação Assistida por IA**: Utilize a IA, idealmente através de um sub-agente validador dedicado, para executar testes automatizados, linters e verificar seu próprio trabalho em relação aos requisitos.
- **Validação Humana**: O desenvolvedor é o responsável final. Realize sempre uma revisão de código (code review) e testes manuais para garantir a qualidade, a correção funcional e a integração da nova funcionalidade.

### 7.4. Ferramentas e Conceitos Chave

- **Slash Commands**: Prompts reutilizáveis e parametrizados que automatizam partes do fluxo de trabalho (ex: `/carregar_contexto`, `/gerar_plano`).
- **Sub-agentes**: Instâncias de IA especializadas com janelas de contexto isoladas. São ideais para tarefas que não devem interferir no contexto principal, como pesquisa aprofundada durante o planejamento ou execução de testes na validação.

---

**Última Atualização:** 2025-11-10

**Versão do Projeto:** 4.0 (Arquitetura Consolidada)
