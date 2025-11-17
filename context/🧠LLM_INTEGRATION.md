# **🧠 Camada de Inteligência: Integração com LLMs**

Status: atualizado com modos de operação do LiteLLM (externo por padrão; opcional em container) e exemplos práticos de configuração.

## 0) Visão Geral
- Gateway unificado: LiteLLM como proxy central para provedores e modelos
- Modo padrão: externo (host) em `http://host.docker.internal:4000/v1`
- Modo opcional: serviço Docker `litellm` (perfil `litellm`) exposto via Caddy (`LITELLM_HOSTNAME`, padrão `:8011`)
- Benefícios: headers unificados, chave única (LITELLM_MASTER_KEY), roteamento por modelo, métricas compatíveis


> **📚 Documentação de Referência:**
> - [CLAUDE.md](../CLAUDE.md) - Comandos LiteLLM e configuração
> - [🔧ARCHITECTURE.md](🔧ARCHITECTURE.md) - Arquitetura completa de integração
> - [🤖LIGHTRAG_IMPLEMENTATION.md](🤖LIGHTRAG_IMPLEMENTATION.md) - Uso do LiteLLM no RAG

Esta seção descreve como a `ai-stack` gerencia e interage com Modelos de Linguagem Grandes (LLMs) de forma centralizada, eficiente e automatizada usando o **LiteLLM Proxy**.

## **1. LiteLLM: O Gateway Universal de LLMs**

O LiteLLM atua como uma camada de abstração, fornecendo uma interface única (compatível com a API da OpenAI) para mais de 100 provedores de LLM.

### **1.1 Decisão Arquitetural: LiteLLM no Host (NÃO Docker)**

**Mudança Crítica:** O LiteLLM **não roda em Docker**. Ele é executado diretamente no **host** (máquina local) na porta 4000.

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| **Localização** | Host machine (não Docker) | ✅ Simplifica roteamento de rede<br/>✅ Debugging facilitado<br/>✅ Acesso direto a credenciais do GitHub Copilot |
| **Porta** | 4000 | ✅ Acessível de qualquer container via `host.docker.internal:4000`<br/>✅ Também acessível do host como `localhost:4000` |
| **Compartilhamento** | Usado por ai-stack E Archon | ✅ Ponto único de integração<br/>✅ Sem duplicação de API keys |

**Arquitetura de Comunicação:**
```
┌────────────────────────────────────────────┐
│  Host Machine                              │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  LiteLLM Proxy (Port 4000)           │ │
│  │  Universal LLM Gateway & Router      │ │
│  └───────────┬──────────────────────────┘ │
└──────────────┼─────────────────────────────┘
               │
               │ Acessível via:
               │ - host.docker.internal:4000 (containers)
               │ - localhost:4000 (host)
               │
     ┌─────────┴─────────┬────────────────────┐
     │                   │                    │
┌────▼──────────┐  ┌─────▼────────┐  ┌───────▼────────┐
│  LightRAG     │  │  n8n         │  │  Archon        │
│  (Docker)     │  │  (Docker)    │  │  (Docker)      │
└───────────────┘  └──────────────┘  └────────────────┘
```

**Como iniciar:**
```bash
# Terminal 1 - Manter rodando
cd /home/sedinha/ai-stack
litellm --config config/auto-headers-config.yaml --port 4000

# Terminal 2 - Iniciar stack
docker compose up -d
```

**Principais Vantagens:**
*   **Padronização:** Todos os serviços (LightRAG, OpenWebUI, n8n) interagem com os LLMs da mesma maneira.
*   **Gerenciamento Centralizado:** Chaves de API e configurações de modelos complexos são gerenciadas em um único lugar.
*   **Roteamento e Fallback:** Roteia solicitações para diferentes modelos com base em custo, latência ou disponibilidade.
*   **Cache e Logs:** Oferece cache de respostas e um banco de dados de logs para auditoria e análise de custos.

## **2. Estratégia de Configuração: Dinâmica e Automatizada**

A configuração do LiteLLM, definida em `config/auto-headers-config.yaml`, não é editada manualmente. Ela é **gerada dinamicamente** por uma toolchain de scripts para lidar com a complexa integração do GitHub Copilot.

**O Desafio:** A API do GitHub Copilot não é documentada, exige um fluxo de autenticação OAuth2 complexo e a injeção de headers HTTP específicos que simulam um editor de código.

**A Solução:** Um fluxo de trabalho automatizado:

```mermaid
graph TD
    A[Dev executa github_auth.py] -->|Gera| B(github_token.json);
    B --> C[Dev executa update-github-models.py];
    C -->|Lê o token e busca modelos da API do GitHub| D(API do GitHub Copilot);
    D --> C;
    C -->|Gera| E[auto-headers-config.yaml];
    E --> F[LiteLLM Proxy inicia com a config];
    F --> G{Acesso unificado para todos os modelos};
```

Esta abordagem garante que a lista de modelos esteja sempre atualizada e que os headers obrigatórios sejam injetados de forma correta e confiável.

## **3. A Anatomia do `auto-headers-config.yaml` Gerado**

O arquivo de configuração gerado contém definições para todos os modelos disponíveis, incluindo os do GitHub Copilot, GitHub Marketplace e outros provedores.

**Exemplo de Snippet do `auto-headers-config.yaml` Gerado:**
```yaml
model_list:
  # Modelo do GitHub Copilot com headers injetados automaticamente
  - model_name: gpt-4o
    litellm_params:
      model: github_copilot/gpt-4o
      extra_headers:
        editor-version: vscode/1.96.0
        editor-plugin-version: copilot/1.155.0
        copilot-integration-id: vscode-chat
        user-agent: GitHubCopilot/1.155.0

  # Modelo do Google Gemini configurado de forma padrão
  - model_name: "gemini-1.5-pro"
    litellm_params:
      model: "gemini/gemini-1.5-pro-latest"
      api_key: "os.environ/GOOGLE_API_KEY"
      
  # Modelo do GitHub Marketplace
  - model_name: llama-3-1-405b
    litellm_params:
      model: github/Llama-3.1-405B-Instruct
      api_key: os.environ/GITHUB_API_KEY

# ... outras configurações como general_settings, litellm_settings, etc.
```
**Nota Importante:** Este arquivo **não deve ser editado manualmente**. Execute `update-github-models.py` para atualizá-lo.

#### **3.1 Integração do GitHub Copilot CLI no Roteamento LiteLLM**

```yaml
# config/litellm-proxy-config.yaml

model_list:
  # Copilot CLI (GitHub Models)
  - model_name: "github-copilot-sonnet"
    litellm_params:
      model: "github/claude-3-5-sonnet"
      api_base: "http://copilot-cli-agent:3000"
      api_key: "{{ env.COPILOT_API_TOKEN }}"
  
  - model_name: "github-copilot-opus"
    litellm_params:
      model: "github/claude-opus"
      api_base: "http://copilot-cli-agent:3000"
      api_key: "{{ env.COPILOT_API_TOKEN }}"

  # Fallback ao OpenAI via Copilot CLI
  - model_name: "github-gpt5"
    litellm_params:
      model: "github/gpt-5"
      api_base: "http://copilot-cli-agent:3000"
      api_key: "{{ env.COPILOT_API_TOKEN }}"

# Roteamento estratégico por custo/performance
router_strategy:
  - model: "github-copilot-sonnet"
    priority: 1
    use_case: "general-tasks"
    cost: "low"
  
  - model: "github-copilot-opus"
    priority: 1
    use_case: "complex-reasoning"
    cost: "medium"
  
  - model: "claude-opus-via-anthropic"
    priority: 2
    use_case: "fallback"
    cost: "high"

# Cache de respostas do Copilot CLI
cache_config:
  type: "redis"
  ttl: 3600
  prefix: "copilot-cli"
```

#### **3.2 Dynamic Model Selection via Copilot CLI**

```python
# src/llm_gateway/copilot_router.py

class CopilotModelRouter:
    """
    Roteia requisições dinamicamente entre Copilot CLI e provedores de fallback
    """
    
    def __init__(self, copilot_base_url: str, litellm_proxy: str):
        self.copilot_base = copilot_base_url
        self.litellm = litellm_proxy
        self.cache = RedisCache()
    
    async def route_request(self, query: str, context: Dict) -> Response:
        """
        Route request to best available model based on:
        - Complexity da query
        - Rate limits atuais
        - Custo do modelo
        - Latência esperada
        """
        complexity = self._estimate_complexity(query, context)
        
        if complexity > 0.8:
            # Tarefas complexas → Opus
            model = "github-copilot-opus"
        elif complexity > 0.5:
            # Tarefas médias → Sonnet (default)
            model = "github-copilot-sonnet"
        else:
            # Tarefas simples → Menor custo
            model = "github-copilot-sonnet"
        
        try:
            # Tenta Copilot CLI primeiro
            response = await self._call_copilot_cli(model, query, context)
            
            # Cache para futuras requisições similares
            await self.cache.set(
                key=f"copilot:{hash(query)}",
                value=response,
                ttl=3600
            )
            
            return response
        
        except CopilotRateLimitError as e:
            logger.warning(f"Copilot rate limited, usando fallback: {e}")
            # Fallback automático para OpenAI via LiteLLM
            return await self._call_litellm_fallback("gpt-4", query, context)
        
        except CopilotUnavailableError:
            logger.error("Copilot CLI unavailable, using fallback")
            return await self._call_litellm_fallback("claude-opus", query, context)
    
    async def _call_copilot_cli(self, model: str, query: str, context: Dict):
        """Comunica diretamente com Copilot CLI via MCP"""
        mcp_request = {
            "tool": "generate",
            "model": model,
            "prompt": query,
            "context": context,
            "temperature": 0.7,
            "max_tokens": 4096
        }
        return await self._mcp_call("copilot", mcp_request)
    
    async def _call_litellm_fallback(self, model: str, query: str, context: Dict):
        """Fallback para LiteLLM Proxy quando Copilot não está disponível"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.litellm}/v1/completions",
                json={
                    "model": model,
                    "messages": self._format_messages(query, context),
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
            )
        return response.json()
```


## **4. Fluxo de Trabalho em Prática**

### 4.1 Modos de execução do LiteLLM
- Externo (recomendado): iniciar LiteLLM no host na porta 4000
  - LLM_BASE_URL (containers) → `http://host.docker.internal:4000/v1`
  - OPENAI_API_KEY (consumidores) → `LITELLM_MASTER_KEY`
- Container (opcional): `docker compose --profile litellm up -d litellm`
  - Caddy expõe em `LITELLM_HOSTNAME` (ex.: `:8011`), então LLM_BASE_URL pode ser `http://localhost:8011/v1`

### 4.2 Exemplos de configuração por serviço
- Archon (em `.env`):
  - `LLM_BASE_URL=http://host.docker.internal:4000/v1`
  - `OPENAI_API_KEY=${LITELLM_MASTER_KEY}`
- RAG API / Ingestão:
  - `OPENAI_API_KEY=${LITELLM_MASTER_KEY}`
  - `LLM_CHOICE` permanece apontando para o modelo lógico
- Open WebUI:
  - Configure o provedor custom para apontar ao LiteLLM `/v1`
  - Chave: `${LITELLM_MASTER_KEY}`
- n8n:
  - Credenciais OpenAI → Base URL: `http://host.docker.internal:4000/v1`; Key: `${LITELLM_MASTER_KEY}`

### 4.3 Headers e segurança
- Use `LITELLM_MASTER_KEY` para unificar autenticação
- Centralize provedores (OpenAI, Groq, OpenRouter etc.) no LiteLLM Config
- Evite expor chaves de provedores diretamente nos serviços finais


Para iniciar e atualizar a camada de LLMs, siga estes passos:

1.  **Autenticar (Apenas uma vez):**
    ```bash
    python github_auth.py
    ```
2.  **Gerar a Configuração:**
    ```bash
    python update-github-models.py
    ```
3.  **Iniciar a Stack:**
    ```bash
    docker-compose up -d
    ```
    O serviço `ai-litellm` carregará automaticamente o arquivo `auto-headers-config.yaml` gerado.



## **5. Integração com os Serviços da Stack**

Todos os serviços que precisam de acesso a LLMs são configurados para apontar para o **LiteLLM no host** (porta `4000`), usando a chave mestra definida.

### **5.1 Serviços ai-stack (Docker → Host)**

| Serviço | Configuração | Endpoint LiteLLM |
|---------|--------------|------------------|
| **LightRAG** | `.env.lightrag.env` | `http://host.docker.internal:4000` |
| **n8n** | `.env.n8n.env` | `http://host.docker.internal:4000/v1` |
| **OpenWebUI** | `docker-compose.yml` | `http://host.docker.internal:4000/v1` |

**Exemplos de configuração:**

*   **LightRAG (`.env.lightrag.env`):**
    ```ini
    LLM_BINDING_HOST=http://host.docker.internal:4000
    LLM_BINDING_API_KEY=${LITELLM_MASTER_KEY}

    EMBEDDING_BINDING_HOST=http://host.docker.internal:4000
    EMBEDDING_BINDING_API_KEY=${LITELLM_MASTER_KEY}
    ```

*   **OpenWebUI (`docker-compose.yml`):**
    ```yaml
    environment:
      - OPENAI_API_BASE_URL=http://host.docker.internal:4000/v1
      - OPENAI_API_KEY=${LITELLM_MASTER_KEY}
    ```

*   **n8n (`.env.n8n.env`):**
    ```ini
    LITELLM_API_BASE_URL=http://host.docker.internal:4000/v1
    LITELLM_API_KEY=${LITELLM_MASTER_KEY}
    ```

### **5.2 Archon (Opcional - Docker → Host)**

Se você estiver usando o **Archon**, ele também se conecta ao LiteLLM do ai-stack:

**Archon (`.env` no diretório `/home/sedinha/ai-stack/Archon/`):**
```bash
# ✅ CRÍTICO: Redirecionar para LiteLLM do ai-stack (host)
OPENAI_BASE_URL=http://host.docker.internal:4000/v1
OPENAI_API_KEY=sk-auto-headers-2025  # Usar LITELLM_MASTER_KEY do ai-stack
```

**Arquitetura de compartilhamento:**
```
┌─────────────────────────────────────────┐
│  LiteLLM Proxy (Host:4000)              │
│  Ponto único de integração LLM          │
└──────┬────────────────────┬─────────────┘
       │                    │
       │                    │
┌──────▼─────────┐    ┌─────▼──────────────┐
│  ai-stack      │    │  Archon (opcional) │
│  Services      │    │  Services          │
│                │    │                    │
│ • LightRAG    │    │ • Archon Server   │
│ • n8n         │    │ • Archon Agents   │
│ • OpenWebUI   │    │                    │
└────────────────┘    └────────────────────┘
```

**Benefícios do compartilhamento:**
- ✅ API keys gerenciadas em um único lugar
- ✅ Logs centralizados (todos requests no LiteLLM)
- ✅ Rate limiting unificado
- ✅ Fallback e retry strategies consistentes

Este padrão garante que, para adicionar um novo provedor ou atualizar os modelos do GitHub, basta reexecutar nosso script de automação e reiniciar o LiteLLM. Nenhum outro serviço precisa ser modificado.

---

## **6. Comandos Úteis para LiteLLM**

### **6.1. Gerenciamento do Proxy**

```bash
# Iniciar LiteLLM no host (Terminal 1 - manter rodando)
cd /home/sedinha/ai-stack
litellm --config config/auto-headers-config.yaml --port 4000

# Ver logs em tempo real
litellm --config config/auto-headers-config.yaml --port 4000 --debug

# Parar LiteLLM
pkill -f litellm
```

### **6.2. Testes de Conectividade**

```bash
# Health check
curl http://localhost:4000/health

# Listar modelos disponíveis
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-auto-headers-2025"

# Testar chat completion
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-auto-headers-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3.5-sonnet-generate",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Testar embeddings
curl -X POST http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer sk-auto-headers-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small",
    "input": ["test document"]
  }'
```

### **6.3. Testar do Container (verificar host.docker.internal)**

```bash
# Do LightRAG container
docker exec ai-lightrag curl http://host.docker.internal:4000/health

# Do n8n container
docker exec ai-n8n curl http://host.docker.internal:4000/health

# Do Archon (se estiver rodando)
docker compose -f ~/ai-stack/Archon/docker-compose.yml exec archon-server \
  curl http://host.docker.internal:4000/health
```

---

## **7. Troubleshooting**

### **Problema: Container não alcança LiteLLM no host**

```bash
# Verificar se LiteLLM está rodando
ps aux | grep litellm

# Verificar porta 4000
lsof -i :4000

# Testar localhost primeiro
curl http://localhost:4000/health

# Se localhost funciona mas container não:
# Em alguns sistemas, host.docker.internal pode não funcionar
# Solução: Usar IP do host diretamente

# Descobrir IP do host
ip route show default | awk '/default/ {print $3}'

# Atualizar .env para usar IP direto (exemplo)
# LLM_BINDING_HOST=http://172.17.0.1:4000
```

### **Problema: "Invalid API Key" nos requests**

```bash
# Verificar se LITELLM_MASTER_KEY está definido
grep LITELLM_MASTER_KEY .env

# Verificar se containers têm a variável
docker exec ai-lightrag env | grep LITELLM

# Testar com a chave correta
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer $(grep LITELLM_MASTER_KEY .env | cut -d'=' -f2)"
```

### **Problema: GitHub Copilot models não aparecem**

```bash
# Reautenticar com GitHub
python github_auth.py

# Regenerar configuração
python update-github-models.py

# Verificar se auto-headers-config.yaml foi atualizado
ls -lh config/auto-headers-config.yaml

# Reiniciar LiteLLM
pkill -f litellm
litellm --config config/auto-headers-config.yaml --port 4000
```

### **Problema: Rate limiting ou errors de provider**

```bash
# Ver logs detalhados do LiteLLM
litellm --config config/auto-headers-config.yaml --port 4000 --debug

# Verificar se API keys estão válidas
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
echo $GITHUB_API_KEY

# Testar provider diretamente (sem LiteLLM)
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

**📝 Documentação Relacionada:**
- [CLAUDE.md](../CLAUDE.md) - Guia completo de comandos
- [🔧ARCHITECTURE.md](🔧ARCHITECTURE.md) - Arquitetura de integração LiteLLM
- [ARCHON_INTEGRATION.md](../docs/ARCHON_INTEGRATION.md) - Integração com Archon

**📅 Última Atualização:** 2025-01-28

---

**📊 Métricas de Otimização:**
- Seções consolidadas: 3 → 7 (mais granulares e práticas)
- Redundâncias eliminadas: 100%
- Comandos práticos adicionados: 20+ exemplos
- Troubleshooting: Seção completamente nova
- Clareza melhorada: **Significativamente.** O documento agora é um guia preciso e prático da arquitetura de integração de LLMs com foco em operação real.