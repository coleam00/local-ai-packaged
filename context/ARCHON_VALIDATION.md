# 🧪 ARCHON_VALIDATION_GUIDE.md
## Scripts e Comandos de Validação Completos

> Guia prático para validar cada etapa da integração Archon + ai-stack + LiteLLM

---

## **PARTE 1: Validação Pré-Startup**

### **1.1 Verificar Ambiente do Host**

```bash
#!/bin/bash
# validate-host-setup.sh

echo "===== VALIDAÇÃO DO AMBIENTE HOST ====="
echo ""

# Verificar Docker
echo "✓ Verificando Docker..."
docker --version || echo "❌ Docker não encontrado"
docker-compose --version || echo "❌ Docker Compose não encontrado"

# Verificar portas livres
echo ""
echo "✓ Verificando disponibilidade de portas..."
PORTS=(4000 3737 8181 8051 8052 5432 5678 7474 7687 9621 3001 9000)

for port in "${PORTS[@]}"; do
    if lsof -i ":$port" > /dev/null 2>&1; then
        echo "⚠️  Porta $port em USO (pode causar conflito)"
        lsof -i ":$port" | tail -1
    else
        echo "✅ Porta $port livre"
    fi
done

# Verificar diretórios necessários
echo ""
echo "✓ Verificando diretórios do projeto..."
[ -d ~/ai-stack ] && echo "✅ ~/ai-stack existe" || echo "❌ ~/ai-stack não encontrado"
[ -d ~/archon ] && echo "✅ ~/archon existe" || echo "❌ ~/archon não encontrado"

# Verificar arquivos de configuração
echo ""
echo "✓ Verificando arquivos de configuração..."
[ -f ~/ai-stack/.env ] && echo "✅ ai-stack/.env existe" || echo "❌ ai-stack/.env não encontrado"
[ -f ~/archon/.env ] && echo "✅ archon/.env existe" || echo "⚠️  archon/.env não encontrado (será necessário criar)"

# Verificar Python/LiteLLM
echo ""
echo "✓ Verificando LiteLLM..."
which litellm > /dev/null 2>&1 && echo "✅ LiteLLM instalado" || echo "❌ LiteLLM não instalado: pip install litellm"

echo ""
echo "===== FIM DA VALIDAÇÃO PRÉ-STARTUP ====="
```

**Executar:**
```bash
chmod +x validate-host-setup.sh
./validate-host-setup.sh
```

---

### **1.2 Verificar Variáveis de Ambiente Críticas**

```bash
#!/bin/bash
# validate-env-vars.sh

echo "===== VALIDAÇÃO DE VARIÁVEIS DE AMBIENTE ====="
echo ""

# Validar ai-stack
echo "🔍 Validando ~/.ai-stack/.env..."
if [ -f ~/ai-stack/.env ]; then
    grep "LITELLM_MASTER_KEY" ~/ai-stack/.env > /dev/null && \
        echo "✅ LITELLM_MASTER_KEY definida" || \
        echo "❌ LITELLM_MASTER_KEY não definida"
    
    grep "LITELLM_HOST" ~/ai-stack/.env > /dev/null && \
        echo "✅ LITELLM_HOST definida" || \
        echo "⚠️  LITELLM_HOST pode não estar configurada"
else
    echo "❌ ~/ai-stack/.env não encontrado"
fi

echo ""

# Validar Archon
echo "🔍 Validando ~/archon/.env..."
if [ -f ~/archon/.env ]; then
    # Verificar SUPABASE
    if grep -q "SUPABASE_URL" ~/archon/.env; then
        URL=$(grep "SUPABASE_URL" ~/archon/.env | cut -d'=' -f2)
        if [[ $URL == https://*.supabase.co ]]; then
            echo "✅ SUPABASE_URL válida: $URL"
        else
            echo "⚠️  SUPABASE_URL pode estar inválida: $URL"
        fi
    else
        echo "❌ SUPABASE_URL não definida"
    fi
    
    # Verificar OPENAI_BASE_URL
    if grep -q "OPENAI_BASE_URL" ~/archon/.env; then
        BASE_URL=$(grep "OPENAI_BASE_URL" ~/archon/.env | cut -d'=' -f2)
        if [[ $BASE_URL == *"4000"* ]]; then
            echo "✅ OPENAI_BASE_URL aponta para LiteLLM: $BASE_URL"
        else
            echo "❌ OPENAI_BASE_URL não aponta para LiteLLM: $BASE_URL"
        fi
    else
        echo "❌ OPENAI_BASE_URL não definida (CRÍTICO!)"
    fi
    
    # Verificar OPENAI_API_KEY
    grep -q "OPENAI_API_KEY" ~/archon/.env && \
        echo "✅ OPENAI_API_KEY definida" || \
        echo "❌ OPENAI_API_KEY não definida"
    
    # Verificar SUPABASE_SERVICE_KEY
    grep -q "SUPABASE_SERVICE_KEY" ~/archon/.env && \
        echo "✅ SUPABASE_SERVICE_KEY definida" || \
        echo "❌ SUPABASE_SERVICE_KEY não definida"
else
    echo "❌ ~/archon/.env não encontrado"
fi

echo ""
echo "===== FIM DA VALIDAÇÃO DE VARIÁVEIS ====="
```

**Executar:**
```bash
chmod +x validate-env-vars.sh
./validate-env-vars.sh
```

---

## **PARTE 2: Validação During Startup**

### **2.1 Iniciar e Monitorar ai-stack**

```bash
#!/bin/bash
# startup-aistack.sh

echo "===== INICIANDO AI-STACK ====="
cd ~/ai-stack

echo ""
echo "1️⃣  Iniciando LiteLLM (Terminal dedicado recomendado)..."
echo "Execute em outro terminal:"
echo "  litellm --config config/litellm-config.yaml --port 4000"
echo ""
read -p "Pressione ENTER após iniciar LiteLLM..."

echo ""
echo "2️⃣  Iniciando stack Docker..."
docker compose up -d

echo ""
echo "3️⃣  Aguardando inicialização (30-60 segundos)..."
sleep 30

echo ""
echo "4️⃣  Verificando status dos containers..."
docker compose ps

echo ""
echo "===== VALIDAÇÃO DE SAÚDE DO AI-STACK ====="

# Verificar PostgreSQL
echo "📊 PostgreSQL:"
docker compose exec -T postgres pg_isready -U postgres 2>/dev/null && \
    echo "✅ PostgreSQL está pronto" || \
    echo "⚠️  PostgreSQL ainda inicializando"

# Verificar Neo4j
echo ""
echo "📈 Neo4j:"
curl -s http://localhost:7474 > /dev/null && \
    echo "✅ Neo4j disponível" || \
    echo "⚠️  Neo4j indisponível"

# Verificar LightRAG
echo ""
echo "🧠 LightRAG:"
curl -s http://localhost:9621/health 2>/dev/null | grep -q "healthy" && \
    echo "✅ LightRAG saudável" || \
    echo "⚠️  LightRAG ainda inicializando"

# Verificar n8n
echo ""
echo "⚙️  n8n:"
curl -s -I http://localhost:5678 | grep -q "200\|301\|302" && \
    echo "✅ n8n disponível" || \
    echo "⚠️  n8n indisponível"

# Verificar OpenWebUI
echo ""
echo "🌐 OpenWebUI:"
curl -s -I http://localhost:3001 | grep -q "200\|301\|302" && \
    echo "✅ OpenWebUI disponível" || \
    echo "⚠️  OpenWebUI indisponível"

echo ""
echo "===== FIM DO STARTUP AI-STACK ====="
```

**Executar:**
```bash
chmod +x startup-aistack.sh
./startup-aistack.sh
```

---

### **2.2 Iniciar e Monitorar Archon**

```bash
#!/bin/bash
# startup-archon.sh

echo "===== INICIANDO ARCHON ====="
cd ~/archon

echo ""
echo "1️⃣  Verificando arquivo .env..."
if [ ! -f .env ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "Execute: cp .env.example .env"
    echo "E configure as variáveis de ambiente."
    exit 1
fi

echo "✅ Arquivo .env encontrado"

echo ""
echo "2️⃣  Iniciando Archon (com logs visíveis)..."
echo "Execute em outro terminal para ver logs em tempo real:"
echo "  cd ~/archon && docker compose logs -f archon-server"
echo ""

docker compose up -d

echo ""
echo "3️⃣  Aguardando inicialização (15-30 segundos)..."
sleep 15

echo ""
echo "4️⃣  Verificando status dos containers..."
docker compose ps

echo ""
echo "===== VALIDAÇÃO DE SAÚDE DO ARCHON ====="

# Verificar Archon Server
echo "🔗 Archon Server (8181):"
curl -s http://localhost:8181/health 2>/dev/null && \
    echo "✅ Archon Server saudável" || \
    echo "⚠️  Archon Server indisponível"

# Verificar Archon UI
echo ""
echo "🖥️  Archon UI (3737):"
curl -s -I http://localhost:3737 2>/dev/null | grep -q "200\|301\|302\|404" && \
    echo "✅ Archon UI disponível" || \
    echo "⚠️  Archon UI indisponível"

# Verificar Archon MCP
echo ""
echo "🔌 Archon MCP (8051):"
curl -s http://localhost:8051/health 2>/dev/null && \
    echo "✅ Archon MCP disponível" || \
    echo "⚠️  Archon MCP indisponível"

# Verificar Archon Agents
echo ""
echo "🤖 Archon Agents (8052):"
curl -s http://localhost:8052/health 2>/dev/null && \
    echo "✅ Archon Agents disponível" || \
    echo "⚠️  Archon Agents indisponível"

echo ""
echo "===== FIM DO STARTUP ARCHON ====="
```

**Executar:**
```bash
chmod +x startup-archon.sh
./startup-archon.sh
```

---

## **PARTE 3: Validação Pós-Startup (Integração)**

### **3.1 Testar Integração LiteLLM ↔ Archon**

```bash
#!/bin/bash
# test-litellm-archon-integration.sh

echo "===== TESTE DE INTEGRAÇÃO LITELLM ↔ ARCHON ====="
echo ""

# 1. Verificar se LiteLLM está rodando
echo "1️⃣  Verificando LiteLLM no host..."
if curl -s http://localhost:4000/v1/models > /dev/null 2>&1; then
    echo "✅ LiteLLM está respondendo"
    MODEL_COUNT=$(curl -s http://localhost:4000/v1/models | grep -o "model_name" | wc -l)
    echo "   Modelos disponíveis: $MODEL_COUNT"
else
    echo "❌ LiteLLM não está respondendo na porta 4000"
    exit 1
fi

echo ""

# 2. Verificar conectividade do Archon com LiteLLM
echo "2️⃣  Verificando se Archon consegue acessar LiteLLM..."
RESULT=$(docker compose -f ~/archon/docker-compose.yml exec -T archon-server \
    curl -s http://host.docker.internal:4000/v1/models 2>/dev/null)

if echo "$RESULT" | grep -q "object"; then
    echo "✅ Archon consegue acessar LiteLLM"
else
    echo "❌ Archon NÃO consegue acessar LiteLLM"
    echo "   Debug: Verifique OPENAI_BASE_URL no .env"
    echo "   Debug: Tente executar manualmente:"
    echo "   docker compose -f ~/archon/docker-compose.yml exec archon-server bash"
    echo "   curl http://host.docker.internal:4000/v1/models"
fi

echo ""

# 3. Verificar se Archon está usando variáveis corretas
echo "3️⃣  Verificando variáveis de ambiente do Archon..."
OPENAI_BASE=$(docker compose -f ~/archon/docker-compose.yml exec -T archon-server \
    env | grep OPENAI_BASE_URL || echo "")

if [ -z "$OPENAI_BASE" ]; then
    echo "⚠️  OPENAI_BASE_URL não definida no container"
else
    echo "✅ OPENAI_BASE_URL=$OPENAI_BASE"
fi

echo ""

# 4. Fazer chamada de teste (opcional)
echo "4️⃣  Teste de chamada LLM (pressione Ctrl+C para pular)..."
echo ""

# Nota: Este teste requer uma chamada real à API
# Você pode testar manualmente fazendo uma pergunta no Archon UI
echo "   Para testar de verdade:"
echo "   1. Acesse http://localhost:3737"
echo "   2. Faça uma pergunta"
echo "   3. Veja os logs do LiteLLM (Ctrl+C no terminal com logs)"
echo ""

echo "===== FIM DO TESTE DE INTEGRAÇÃO ====="
```

**Executar:**
```bash
chmod +x test-litellm-archon-integration.sh
./test-litellm-archon-integration.sh
```

---

### **3.2 Testar MCP Archon ↔ Claude Code**

```bash
#!/bin/bash
# test-mcp-integration.sh

echo "===== TESTE DE INTEGRAÇÃO MCP ARCHON ↔ CLAUDE CODE ====="
echo ""

# 1. Verificar se Archon MCP está respondendo
echo "1️⃣  Verificando Archon MCP..."
if curl -s http://localhost:8051/health > /dev/null 2>&1; then
    echo "✅ Archon MCP está respondendo"
else
    echo "❌ Archon MCP não está respondendo na porta 8051"
    exit 1
fi

echo ""

# 2. Verificar capabilidades do MCP
echo "2️⃣  Verificando capabilidades do MCP..."
CAPABILITIES=$(curl -s http://localhost:8051/capabilities 2>/dev/null)
if [ -n "$CAPABILITIES" ]; then
    echo "✅ MCP retornou capabilidades"
    echo "   $CAPABILITIES" | head -5
else
    echo "⚠️  MCP não retornou capabilidades explícitas"
fi

echo ""

# 3. Instruções para conectar Claude Code
echo "3️⃣  Conectando Claude Code ao Archon MCP..."
echo ""
echo "   Opção 1: Via CLI"
echo "   $ claude code --mcp \"archon=http://localhost:8051\""
echo ""
echo "   Opção 2: Via Arquivo de Configuração"
echo "   Edite: ~/.local/share/claude-dev/settings.json"
echo ""
echo "   {\"mcpServers\": {\"archon\": {\"url\": \"http://localhost:8051\"}}}"
echo ""

# 4. Teste de comando MCP
echo "4️⃣  Testando comando MCP (se Claude Code estiver conectado)..."
echo "   Execute no Claude Code:"
echo "   @archon list-projects"
echo ""

echo "===== FIM DO TESTE MCP ====="
```

**Executar:**
```bash
chmod +x test-mcp-integration.sh
./test-mcp-integration.sh
```

---

## **PARTE 4: Checklist Completo de Validação**

```bash
#!/bin/bash
# full-validation-checklist.sh

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     CHECKLIST COMPLETO DE VALIDAÇÃO - AI-STACK + ARCHON   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

PASSED=0
FAILED=0
WARNINGS=0

test_item() {
    local description=$1
    local command=$2
    local expected=$3
    
    printf "%-50s " "[$PASSED/$FAILED/$WARNINGS] $description"
    
    RESULT=$(eval "$command" 2>/dev/null)
    
    if [[ "$RESULT" == *"$expected"* ]] || [ -z "$expected" ] && [ -n "$RESULT" ]; then
        echo "✅"
        ((PASSED++))
    elif [[ "$RESULT" == *"$expected"* ]]; then
        echo "⚠️ "
        ((WARNINGS++))
    else
        echo "❌"
        ((FAILED++))
    fi
}

echo "═══════════════════════════════════════════════════════════"
echo "PARTE 1: AMBIENTE HOST"
echo "═══════════════════════════════════════════════════════════"

test_item "Docker instalado" "docker --version" "Docker"
test_item "Docker Compose instalado" "docker-compose --version" "Docker Compose"
test_item "LiteLLM instalado" "which litellm" "litellm"
test_item "ai-stack diretório" "[ -d ~/ai-stack ] && echo ok" "ok"
test_item "Archon diretório" "[ -d ~/archon ] && echo ok" "ok"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "PARTE 2: VARIÁVEIS DE AMBIENTE"
echo "═══════════════════════════════════════════════════════════"

test_item "ai-stack .env" "[ -f ~/ai-stack/.env ] && echo ok" "ok"
test_item "Archon .env" "[ -f ~/archon/.env ] && echo ok" "ok"
test_item "LITELLM_MASTER_KEY definida" "grep LITELLM_MASTER_KEY ~/ai-stack/.env" "LITELLM"
test_item "OPENAI_BASE_URL aponta para LiteLLM" "grep 'OPENAI_BASE_URL.*4000' ~/archon/.env" "4000"
test_item "SUPABASE_URL configurada" "grep SUPABASE_URL ~/archon/.env | grep supabase" "supabase"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "PARTE 3: PORTAS DISPONÍVEIS"
echo "═══════════════════════════════════════════════════════════"

for port in 4000 3737 8181 8051 8052 5432 7474 7687 9621 5678 3001 9000; do
    test_item "Porta $port livre" "! lsof -i :$port 2>/dev/null && echo ok" "ok"
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "PARTE 4: CONTAINERS RODANDO"
echo "═══════════════════════════════════════════════════════════"

test_item "PostgreSQL ativo" "docker compose -f ~/ai-stack/docker-compose.yml ps postgres" "postgres.*Up"
test_item "Neo4j ativo" "docker compose -f ~/ai-stack/docker-compose.yml ps neo4j" "neo4j.*Up"
test_item "LightRAG ativo" "docker compose -f ~/ai-stack/docker-compose.yml ps lightrag" "lightrag.*Up"
test_item "Archon Server ativo" "docker compose -f ~/archon/docker-compose.yml ps archon-server" "archon-server.*Up"
test_item "Archon UI ativo" "docker compose -f ~/archon/docker-compose.yml ps archon-ui" "archon-ui.*Up"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "PARTE 5: HEALTH CHECKS"
echo "═══════════════════════════════════════════════════════════"

test_item "LiteLLM respondendo" "curl -s http://localhost:4000/v1/models" "model_name"
test_item "PostgreSQL pronto" "docker compose -f ~/ai-stack/docker-compose.yml exec -T postgres pg_isready -U postgres" "accepting"
test_item "Neo4j disponível" "curl -s http://localhost:7474" "Neo4j"
test_item "LightRAG saudável" "curl -s http://localhost:9621/health" "status"
test_item "Archon Server saudável" "curl -s http://localhost:8181/health" "status"
test_item "Archon MCP disponível" "curl -s http://localhost:8051/health" "status"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "PARTE 6: INTEGRAÇÕES"
echo "═══════════════════════════════════════════════════════════"

test_item "Archon acessa LiteLLM" \
    "docker compose -f ~/archon/docker-compose.yml exec -T archon-server curl -s http://host.docker.internal:4000/v1/models" \
    "object"

test_item "ai-stack conectado ao LiteLLM" \
    "docker compose -f ~/ai-stack/docker-compose.yml exec -T lightrag curl -s http://host.docker.internal:4000/v1/models" \
    "object"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                     RESULTADO FINAL                        ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║ ✅ PASSOU:  $PASSED                                         ║"
echo "║ ⚠️  AVISOS:  $WARNINGS                                      ║"
echo "║ ❌ FALHARAM: $FAILED                                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 TUDO PRONTO! Sistema totalmente integrado e funcional."
    exit 0
else
    echo "⚠️  Existem problemas a resolver. Veja ARCHON_INTEGRATION.md para detalhes."
    exit 1
fi
```

**Executar:**
```bash
chmod +x full-validation-checklist.sh
./full-validation-checklist.sh
```

---

## **PARTE 5: Troubleshooting Avançado**

### **5.1 Debug Detalhado de Conexões**

```bash
#!/bin/bash
# debug-connections.sh

echo "===== DEBUG DETALHADO DE CONEXÕES ====="
echo ""

# Debug LiteLLM
echo "🔍 DEBUG LITELLM"
echo "---------------------"
curl -v http://localhost:4000/v1/models 2>&1 | grep -A 5 "< HTTP"
echo ""

# Debug Archon conectando a LiteLLM
echo "🔍 DEBUG ARCHON → LITELLM"
echo "---------------------"
docker compose -f ~/archon/docker-compose.yml exec archon-server \
    curl -v http://host.docker.internal:4000/v1/models 2>&1 | grep -A 5 "< HTTP"
echo ""

# Debug Variáveis de Ambiente
echo "🔍 DEBUG VARIÁVEIS ARCHON"
echo "---------------------"
docker compose -f ~/archon/docker-compose.yml exec archon-server env | grep -i "openai\|litellm"
echo ""

# Debug Logs do Archon
echo "🔍 DEBUG LOGS ARCHON"
echo "---------------------"
docker compose -f ~/archon/docker-compose.yml logs --tail=50 archon-server
echo ""

echo "===== FIM DO DEBUG ====="
```

---

## **REFERÊNCIA RÁPIDA**

| Componente | Status Check | Logs | Restart |
|-----------|---|---|---|
| LiteLLM | `curl http://localhost:4000/v1/models` | Terminal dedicado | `litellm...` |
| PostgreSQL | `docker compose -f ~/ai-stack/docker-compose.yml exec -T postgres pg_isready` | `docker compose logs postgres` | `docker compose restart postgres` |
| Neo4j | `curl http://localhost:7474` | `docker compose logs neo4j` | `docker compose restart neo4j` |
| LightRAG | `curl http://localhost:9621/health` | `docker compose logs lightrag` | `docker compose restart lightrag` |
| Archon Server | `curl http://localhost:8181/health` | `docker compose -f ~/archon logs archon-server` | `docker compose -f ~/archon restart archon-server` |
| Archon MCP | `curl http://localhost:8051/health` | `docker compose -f ~/archon logs archon-mcp` | `docker compose -f ~/archon restart archon-mcp` |
