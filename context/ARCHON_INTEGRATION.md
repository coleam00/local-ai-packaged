# 🔗 ARCHON_INTEGRATION.md
## Integração Modular: Archon + ai-stack com LiteLLM

> **Decisão Arquitetural:** Manter `ai-stack` e `Archon` como stacks **completamente independentes**, conectadas apenas via **LiteLLM Proxy** no host.

---

## **1. Estado Atual vs. Estado Desejado**

### **Problemas Pendentes Identificados**

| Problema | Causa Raiz | Status | Solução |
|----------|-----------|--------|---------|
| Archon container inicia mas não responde | Health checks falhando silenciosamente | 🔴 CRÍTICO | Ver logs em tempo real: `docker compose up` (sem `-d`) |
| `.env` do Archon não configurado | Supabase URL/Keys ausentes | 🔴 CRÍTICO | Preencher credenciais Supabase em `~/archon/.env` |
| Portas em conflito (3737, 8181, 8051) | Sistema local já usa essas portas | 🟡 AVISO | Verificar com `lsof -i :PORTA` e ajustar em `.env` |
| LiteLLM não redireciona Archon | `OPENAI_BASE_URL` não definida | 🔴 CRÍTICO | Adicionar `OPENAI_BASE_URL=http://host.docker.internal:4000/v1` |
| MCP do Archon desconectado do Claude Code | Configuração MCP não implementada | 🟡 TODO | Configurar MCP em `~/.local/share/claude-dev/servers.json` |
| Schema PostgreSQL do Archon conflita com ai-stack | Ambos tentam usar mesmo banco local | 🟢 RESOLVIDO | Archon usa **Supabase Cloud** (banco separado) |
| n8n webhook com GitHub desconectado | Configuração de orquestração incompleta | 🟡 TODO | Implementar após Archon estável |

---

## **2. Arquitetura Final: Modular com Três Camadas**

```
┌──────────────────────────────────────────────────────────────┐
│                   CAMADA 1: HOST (Máquina Local)             │
│                                                              │
│  🎛️ LiteLLM Proxy (Porta 4000) - PONTE UNIVERSAL            │
│  └─ Rota requisições para: OpenAI, Anthropic, GitHub, etc.  │
│                                                              │
│  ⌨️ Claude Code CLI (TTY)                                   │
│  └─ Conecta via MCP ao Archon (localhost:8051)              │
│                                                              │
│  📊 Portainer (Porta 9000) - Gerenciador Docker             │
└──────────────────────────────────────────────────────────────┘
         │                              │
         ├────────────────┬─────────────┤
         │                │             │
    ┌────▼────┐      ┌────▼────┐  ┌───▼────┐
    │ ai-stack │      │  Archon │  │  n8n   │
    │ (Docker) │      │ (Docker)│  │ (host) │
    └──────────┘      └─────────┘  └────────┘
```

### **Camada 2: ai-stack (INTACTO - Independente)**

```yaml
Stack: ~/ai-stack/docker-compose.yml
Permanece: Exatamente como está configurado

Serviços:
  - PostgreSQL + pgvector (5432) → Schema RAG via init-db.sql
  - Neo4j (7474, 7687) → Grafos de conhecimento
  - LightRAG (9621) → Recuperação híbrida
  - OpenWebUI (3001) → Interface de chat
  - Portainer (9000) → Gerenciador de containers

Variáveis de Ambiente:
  LITELLM_HOST=http://host.docker.internal:4000  # ← Aponta para LiteLLM
  LITELLM_MASTER_KEY=sk-1234  # ← Sua master key
```

### **Camada 3: Archon (NOVO - Independente)**

```yaml
Stack: ~/archon/docker-compose.yml
Estado: Novo projeto, configuração modular

Serviços:
  - Supabase Cloud (Banco separado) → Banco de dados do Archon
  - Archon Server (8181) → API principal
  - Archon UI (3737) → Interface web
  - Archon MCP (8051) → Protocolo Model Context
  - Archon Agents (8052) → Agentes autônomos

Variáveis de Ambiente:
  SUPABASE_URL=https://seu-projeto.supabase.co  # ← Cloud
  SUPABASE_SERVICE_KEY=eyJhbGci...  # ← Da Supabase
  OPENAI_BASE_URL=http://host.docker.internal:4000/v1  # ← CRÍTICO!
  OPENAI_API_KEY=sk-1234  # ← LITELLM_MASTER_KEY
```

---

## **3. Resolução Passo-a-Passo dos Problemas**

### **PROBLEMA #1: .env do Archon não configurado** 🔴

**Localização:** `~/archon/.env`

**Solução Completa:**

```bash
# 1. Entrar no diretório Archon
cd ~/archon

# 2. Copiar template
cp .env.example .env

# 3. Editar arquivo
nano .env
```

**Conteúdo necessário do `.env`:**

```ini
# ===== SUPABASE (OBRIGATÓRIO) =====
# Origem: https://supabase.com/dashboard
# 1. Crie projeto gratuito
# 2. Settings → API → Copie Project URL
# 3. Copie service_role secret (chave **longa**)

SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ===== LLM: REDIRECIONAR PARA LITELLM =====
# ESTA é a variável CHAVE que conecta Archon ao seu LiteLLM!

OPENAI_API_KEY=sk-1234  # Usa a LITELLM_MASTER_KEY do seu ai-stack
OPENAI_BASE_URL=http://host.docker.internal:4000/v1  # ← CRÍTICO!

# ===== EMBEDDINGS (opcional) =====
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_PROVIDER=openai

# ===== PORTAS (evitar conflitos com ai-stack) =====
ARCHON_UI_PORT=3737
ARCHON_SERVER_PORT=8181
ARCHON_MCP_PORT=8051
ARCHON_AGENTS_PORT=8052

# ===== HOST =====
HOST=localhost

# ===== OPCIONAL: Logging =====
DEBUG=false
LOG_LEVEL=info
```

**Validação:**
```bash
# Verificar se .env está correto
grep OPENAI_BASE_URL ~/archon/.env
# Deve mostrar: OPENAI_BASE_URL=http://host.docker.internal:4000/v1

grep SUPABASE_URL ~/archon/.env
# Deve mostrar: SUPABASE_URL=https://...supabase.co
```

---

### **PROBLEMA #2: Containers iniciam mas não respondem** 🔴

**Causa:** Health checks falhando silenciosamente quando `-d` (detach) está ativo.

**Solução:**

```bash
cd ~/archon

# PASSO 1: Parar tudo e limpar
docker compose down -v
docker compose down --remove-orphans
docker system prune -a --volumes

# PASSO 2: Iniciar SEM -d (sem detach) para ver logs em tempo real
docker compose up --build

# Você DEVE ver logs como:
# archon-server    | INFO:     Uvicorn running on http://0.0.0.0:8181
# archon-ui        | VITE v5.x.x  ready in xxx ms
# archon-mcp       | INFO:     MCP Server listening on http://0.0.0.0:8051
```

**Se tiver ERRO:**

```bash
# Terminal separado: Ver logs do serviço específico
docker compose logs -f archon-server

# Procure por:
# - "Connection refused" → Supabase não acessível
# - "Invalid API key" → SUPABASE_SERVICE_KEY errada
# - "port already in use" → Ajustar ARCHON_*_PORT no .env
```

**Após confirmar funcionamento:**
```bash
# Ctrl+C para parar (no terminal com logs)

# Agora inicia com -d (background)
docker compose up -d
```

---

### **PROBLEMA #3: Portas em conflito** 🟡

**Verificar quais portas estão em uso:**

```bash
# Verificar portas do Archon
lsof -i :3737
lsof -i :8181
lsof -i :8051
lsof -i :8052

# Se tiver conflito, mate o processo
sudo kill -9 <PID>

# OU altere as portas no .env:
# ARCHON_UI_PORT=3738
# ARCHON_SERVER_PORT=8182
# ARCHON_MCP_PORT=8052
# ARCHON_AGENTS_PORT=8053
```

**Verificar portas do ai-stack:**

```bash
# Se ai-stack estiver rodando:
docker compose -f ~/ai-stack/docker-compose.yml ps

# Deve mostrar:
# supabase-db    | 5432
# neo4j          | 7474, 7687
# lightrag       | 9621
# n8n            | 5678
# openwebui      | 3001
```

---

### **PROBLEMA #4: LiteLLM não redireciona Archon** 🔴

**Validação: LiteLLM deve estar rodando no host**

```bash
# Verificar se LiteLLM está ativo
ps aux | grep litellm

# Se não estiver, iniciar:
cd ~/ai-stack

# Terminal dedicado (deixe rodando):
litellm --config config/litellm-config.yaml --port 4000

# Deve mostrar:
# LiteLLM Proxy started on port 4000
# Model list loaded: X models
```

**Teste de conectividade:**

```bash
# 1. Testar LiteLLM direto (do host)
curl http://localhost:4000/v1/models

# 2. Testar do container Archon
docker compose exec archon-server curl http://host.docker.internal:4000/v1/models

# Se funcionar, Archon consegue acessar LiteLLM!
```

**Verificar configuração no Archon:**

```bash
# Dentro do container Archon
docker compose exec archon-server env | grep -i openai

# Deve mostrar:
# OPENAI_BASE_URL=http://host.docker.internal:4000/v1
# OPENAI_API_KEY=sk-1234
```

---

### **PROBLEMA #5: MCP do Archon desconectado do Claude Code** 🟡

**Passo 1: Verificar se MCP do Archon está funcionando**

```bash
# Testar saúde do MCP
curl http://localhost:8051/health

# Deve retornar algo como:
# {"status": "healthy", "version": "1.0"}
```

**Passo 2: Configurar Claude Code para conectar ao MCP**

Editar: `~/.local/share/claude-dev/settings.json` ou `~/.config/code-server/config.yaml`

```json
{
  "mcpServers": {
    "archon": {
      "command": "curl",
      "args": ["http://localhost:8051"],
      "autoStart": true,
      "alwaysAllow": ["*"]
    }
  },
  "mcp": {
    "enabled": true,
    "timeout": 30000
  }
}
```

**OU usar Claude Code CLI diretamente:**

```bash
# Conectar ao Archon MCP via Claude Code
claude code --mcp "archon=http://localhost:8051"

# Agora pode usar comandos como:
# "List all my Archon projects"
# "Add task to project"
# "Get knowledge base summary"
```

**Teste de Conectividade:**

```bash
# Claude Code deve conseguir chamar ferramentas do Archon
claude code --exec "@archon list-projects"

# Se funcionar, MCP está conectado!
```

---

## **4. Checklist de Validação Completa**

Depois de resolver todos os problemas:

```bash
# ✅ VALIDAÇÃO 1: ai-stack funcionando
curl http://localhost:9621/health  # LightRAG
curl http://localhost:5432 2>/dev/null || echo "PostgreSQL ativo"
docker compose -f ~/ai-stack/docker-compose.yml ps

# ✅ VALIDAÇÃO 2: LiteLLM rodando (no host)
curl http://localhost:4000/v1/models | grep -q model_name && echo "LiteLLM ativo" || echo "ERRO!"

# ✅ VALIDAÇÃO 3: Archon funcionando
curl http://localhost:8181/health
curl http://localhost:3737
curl http://localhost:8051/health

# ✅ VALIDAÇÃO 4: Variáveis de ambiente corretas
grep OPENAI_BASE_URL ~/archon/.env | grep host.docker.internal
grep SUPABASE_URL ~/archon/.env | grep supabase.co

# ✅ VALIDAÇÃO 5: MCP conectado
curl http://localhost:8051/capabilities

# ✅ VALIDAÇÃO 6: LiteLLM recebendo requisições
# (Faça uma pergunta no Archon UI e veja os logs do LiteLLM)
docker compose -f ~/archon/docker-compose.yml logs archon-server | grep OpenAI
```

---

## **5. Mapa de Portas Final (Sem Conflitos)**

| Serviço | Porta | Stack | Status |
|---------|-------|-------|--------|
| **LiteLLM Proxy** | 4000 | Host | ✅ Ponte universal |
| PostgreSQL (ai-stack) | 5432 | ai-stack | ✅ RAG data |
| Neo4j Browser | 7474 | ai-stack | ✅ Graph UI |
| Neo4j Bolt | 7687 | ai-stack | ✅ Graph DB |
| LightRAG API | 9621 | ai-stack | ✅ Recuperação |
| n8n | 5678 | ai-stack | ✅ Orquestração |
| OpenWebUI | 3001 | ai-stack | ✅ Chat interface |
| Portainer | 9000 | ai-stack | ✅ Docker manager |
| **Archon UI** | **3737** | **Archon** | **✅ Interface** |
| **Archon Server** | **8181** | **Archon** | **✅ API** |
| **Archon MCP** | **8051** | **Archon** | **✅ Protocol** |
| **Archon Agents** | **8052** | **Archon** | **✅ Tasks** |

---

## **6. Sequência de Startup Recomendada**

**Ordem Correta para evitar problemas:**

```bash
# ===== 1. HOST (Terminal 1) =====
cd ~/ai-stack
litellm --config config/litellm-config.yaml --port 4000
# Aguarde: "LiteLLM Proxy started on port 4000"

# ===== 2. AI-STACK (Terminal 2) =====
cd ~/ai-stack
docker compose up -d
# Aguarde 30-60 segundos para inicialização

# ===== 3. VALIDAR AI-STACK (Terminal 3) =====
curl http://localhost:9621/health
docker compose -f ~/ai-stack/docker-compose.yml ps

# ===== 4. ARCHON (Terminal 2, após ai-stack estável) =====
cd ~/archon
docker compose up -d
# Aguarde 15-30 segundos

# ===== 5. VALIDAR ARCHON (Terminal 3) =====
curl http://localhost:8181/health
curl http://localhost:3737
docker compose -f ~/archon/docker-compose.yml ps

# ===== 6. TESTE INTEGRAÇÃO (Terminal 3) =====
# No Archon UI (http://localhost:3737), faça uma pergunta
# Nos logs do LiteLLM (Terminal 1), deve aparecer:
# POST /v1/chat/completions - 200 OK

# ===== 7. CONECTAR CLAUDE CODE (Terminal 4) =====
claude code --mcp "archon=http://localhost:8051"
claude code --exec "@archon list-projects"
```

---

## **7. Troubleshooting Rápido**

### **Problema: "Connection refused" no Archon**

```bash
# 1. Verificar se Supabase está acessível
curl https://seu-projeto.supabase.co

# 2. Validar credenciais
grep SUPABASE ~/.archon/.env

# 3. Testar de dentro do container
docker compose exec archon-server curl -v https://seu-projeto.supabase.co
```

### **Problema: "Invalid API key"**

```bash
# 1. Verificar chave Supabase
# Ir em supabase.com → Settings → API → Copiar service_role secret novamente

# 2. Atualizar .env
nano ~/archon/.env

# 3. Reiniciar container
docker compose restart archon-server
```

### **Problema: LiteLLM não responde do Archon**

```bash
# 1. Verificar se LiteLLM está rodando (no host)
ps aux | grep litellm

# 2. Testar conectividade
docker compose exec archon-server ping host.docker.internal
docker compose exec archon-server curl http://host.docker.internal:4000/models

# 3. Se falhar, adicionar ao /etc/hosts (Linux)
echo "127.0.0.1 host.docker.internal" | sudo tee -a /etc/hosts

# 4. No macOS/Windows, já está configurado automaticamente
```

---

## **8. Próximos Passos (Após Estabilização)**

### **Fase 2: Integração Avançada**

- [ ] Configurar n8n webhook com GitHub (automação de tasks)
- [ ] Implementar sistema de approval em n8n
- [ ] Conectar Claude Code a ambas as stacks via MCP router
- [ ] Configurar logging centralizado (observabilidade)

### **Fase 3: Produção**

- [ ] Implementar backup automático do Supabase
- [ ] Configurar SSL/TLS para endpoints
- [ ] Implementar rate limiting no LiteLLM
- [ ] Setup de monitoramento (Prometheus + Grafana)

---

## **Referências**

- **ARCHON_GUIDE.md:** Guia modular do Archon
- **DATABASE_SETUP.md:** Schema PostgreSQL do ai-stack
- **LLM_INTEGRATION.md:** Configuração do LiteLLM
- **ARCHITECTURE.md:** Arquitetura global da ai-stack
