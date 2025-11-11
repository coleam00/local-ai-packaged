# 🎛️ PORTAINER_SETUP.md - Gerenciamento Visual da AI-Stack

## 📚 Missão da Documentação

Este documento fornece um guia completo para utilizar **Portainer** como ferramenta de gerenciamento, monitoramento e depuração visual para toda a **AI-Stack**. Ele cobre desde a configuração inicial até operações avançadas.

---

## 🎯 O Que é Portainer e Por Que Usar?

### Definição

**Portainer** é uma interface web de gerenciamento de containers Docker que permite:
- ✅ Visualizar todos os containers em tempo real
- ✅ Acessar logs de cada container
- ✅ Abrir terminais dentro de containers (docker exec)
- ✅ Gerenciar ciclo de vida (start/stop/restart)
- ✅ Visualizar configurações, variáveis de ambiente, volumes
- ✅ Organizar containers em "stacks"

### Por Que Usar com AI-Stack?

| Tarefa | Terminal | Portainer |
|--------|----------|-----------|
| **Ver logs de LightRAG** | `docker logs ai-lightrag` | UI visual, tempo real |
| **Executar comando em container** | `docker exec -it supabase-db psql...` | Exec Console na UI |
| **Reiniciar um serviço** | `docker-compose restart lightrag` | Um clique |
| **Verificar config de container** | `docker inspect ai-plane-api` | UI organizada |
| **Debugar toda a stack** | Multiple CLI commands | Um painel centralizado |

---

## 🚀 FASE 1: Acesso e Configuração Inicial

### Passo 1: Acessar Portainer

**URL:** `http://localhost:9000`

**Primeira Vez (Setup Inicial):**

1. Abra seu navegador
2. Vá para `http://localhost:9000`
3. Você verá a tela **"Create administrator user"**

### Passo 2: Criar Usuário Administrador

Na primeira vez, você precisa criar as credenciais admin:

```
Username:  admin
Password:  SUA_SENHA_FORTE_AQUI
Confirm:   Mesma senha
```

**Recomendação:** Use uma senha forte com:
- Mínimo 12 caracteres
- Letras maiúsculas e minúsculas
- Números e símbolos
- Exemplo: `Port@iner2025!aiStack`

Clique em **"Create user"**.

### Passo 3: Conectar ao Ambiente Docker Local

Após criar o usuário, Portainer perguntará qual ambiente gerenciar.

**Opção 1: Docker Local (Recomendado)**

Selecione: **"Docker"** ou **"Docker Local"**

Portainer tentará conectar automaticamente ao Docker daemon do seu host.

**Se conectar automaticamente:**
- ✅ Você verá "✅ Environment connected"
- ✅ Clique em "Connect"
- ✅ Você será redirecionado ao Dashboard

**Se não conectar automaticamente:**

```bash
# Verifique se docker está rodando
docker ps

# Verifique permissões do socket Docker
ls -la /var/run/docker.sock

# Portainer pode precisar de acesso ao socket
# Se houver erro de permissão, execute:
sudo usermod -aG docker $USER
newgrp docker  # Ativa novo grupo
```

### Passo 4: Dashboard Inicial

Após conectar, você verá:

```
┌─────────────────────────────────────────┐
│    PORTAINER DASHBOARD                  │
├─────────────────────────────────────────┤
│                                         │
│  Environment Status                     │
│  ✅ Docker                              │
│                                         │
│  Quick Actions                          │
│  • Containers: XX running               │
│  • Images: XX available                 │
│  • Volumes: XX in use                   │
│                                         │
│  Left Sidebar:                          │
│  └─ Dashboard                           │
│  └─ Containers                          │
│  └─ Images                              │
│  └─ Volumes                             │
│  └─ Networks                            │
│  └─ Stacks                              │
│                                         │
└─────────────────────────────────────────┘
```

**Parabéns! Portainer está configurado.**

---

## 🏗️ FASE 2: Gerenciamento da AI-Stack

### O Conceito de "Stacks" no Portainer

Uma **Stack** no Portainer é uma coleção de containers definida por um arquivo `docker-compose.yml`. Ele facilita:
- Visualizar todos os containers da stack em um único lugar
- Gerenciar o ciclo de vida completo (stop/start/restart)
- Atualizar configurações
- Deletar ou criar novas stacks

### Passo 1: Importar/Associar AI-Stack

**Opção A: Criar Stack a partir do arquivo docker-compose.yml**

1. Clique em **"Stacks"** no menu esquerdo
2. Clique em **"Add Stack"** (botão azul no canto superior)
3. Escolha **"Stack > Build Method"**:
   - **Recomendado: "Web editor"** (para editar inline)
   - Ou **"Upload"** (se tiver arquivo local)

4. **Se usar "Web editor":**
   - Cole o conteúdo do seu `docker-compose.yml`
   - Nomeie a stack: `ai-stack`
   - Role para baixo e clique **"Deploy the stack"**

5. **Se usar "Upload":**
   - Selecione seu arquivo `docker-compose-OPCAO2.yml`
   - Nomeie: `ai-stack`
   - Clique **"Deploy"**

### Passo 2: Visualizar Containers da Stack

Após deploy, você será redirecionado para a página da stack.

**Você verá uma tabela:**

```
┌────────────────────────────────────────────┐
│ AI-STACK Containers                        │
├────────────────────────────────────────────┤
│ Name              Status    Image          │
├────────────────────────────────────────────┤
│ supabase-db       Running   supabase/...   │
│ postgres-plane    Running   postgres:15    │
│ supabase-studio   Running   supabase/...   │
│ supabase-kong     Running   kong:2.8       │
│ supabase-auth     Running   supabase/...   │
│ ai-lightrag       Running   lightrag:...   │
│ ai-n8n            Running   n8nio/n8n      │
│ ai-neo4j          Running   neo4j:5.15     │
│ ai-openwebui      Running   ghcr.io/...    │
│ ai-plane-api      Running   makeplane/...  │
│ ai-plane-web      Running   makeplane/...  │
│ ai-portainer      Running   portainer/...  │
│ ... (mais containers)                      │
└────────────────────────────────────────────┘
```

**Cada container tem ações disponíveis:**
- 🔍 Inspecionar (ver configuração)
- 📋 Logs (visualizar output)
- ⚡ Exec Console (abrir terminal)
- ⏹️ Stop (parar)
- ▶️ Start (iniciar)
- 🔄 Restart (reiniciar)
- 🗑️ Delete (remover)

---

## 🔧 FASE 3: Operações Essenciais via Portainer

### Operação 1: Visualizar Logs em Tempo Real

**Cenário:** Você quer debugar erros de LightRAG

**Via Terminal:**
```bash
docker logs -f ai-lightrag  # -f = follow (tempo real)
```

**Via Portainer:**

1. Vá para **"Containers"** no menu esquerdo
2. Procure por **"ai-lightrag"** na lista
3. Clique no nome do container
4. Você verá:
   - Nome, status, imagem
   - Logs em tempo real na aba **"Logs"**
   - Auto-scroll habilitado
5. Para filtrar logs:
   - Use **"Filter"** para buscar keywords
   - Exemplo: Busque por "error" para ver apenas erros

**Vantagem:** Visualização visual, cores destacadas, time-stamps claros

---

### Operação 2: Acessar Terminal (Exec Console)

**Cenário:** Você precisa executar um comando dentro de um container

**Exemplo: Validar Schema RAG**

Via Terminal:
```bash
docker exec -i supabase-db psql -U supabase_admin -d postgres -c "\dt rag.*"
```

Via Portainer:

1. **Containers** → Procure por **"supabase-db"**
2. Clique no nome do container
3. Procure pela aba **"Exec Console"** ou **"Exec"**
4. Você verá um terminal interativo:

```
┌──────────────────────────────────────────────┐
│ EXEC CONSOLE - supabase-db                   │
├──────────────────────────────────────────────┤
│ User: root (ou você pode mudar)              │
│ Cmd:  /bin/sh (ou /bin/bash)                 │
│                                              │
│ [Terminal console aqui]                      │
│ # psql -U supabase_admin -d postgres ...     │
│                                              │
└──────────────────────────────────────────────┘
```

5. Execute comandos diretamente:

```bash
# Validar tabelas RAG
psql -U supabase_admin -d postgres -c "\dt rag.*"

# Verificar usuários
psql -U supabase_admin -d postgres -c "\du"

# Testar INSERT
psql -U supabase_admin -d postgres -c "INSERT INTO rag.sources (url, source_type) VALUES ('test', 'test');"
```

**Vantagem:** Sem precisar abrir terminal local, tudo na UI

---

### Operação 3: Reiniciar/Parar/Iniciar Serviços

**Cenário: LightRAG travou, você quer reiniciar**

Via Terminal:
```bash
docker-compose restart ai-lightrag
```

Via Portainer:

1. **Containers** → Procure por **"ai-lightrag"**
2. Clique para ver detalhes
3. Procure pelos botões de ação no topo:

```
[■ STOP]  [▶ START]  [↻ RESTART]  [⚙ INSPECT]
```

4. Clique em **"RESTART"**
5. O container será parado e reiniciado
6. Você verá a mudança de status em tempo real

**Status possíveis:**
- 🟢 **Running** (verde, operacional)
- 🔴 **Stopped** (vermelho, parado)
- 🟡 **Exited** (amarelo, saiu com erro)
- 🟠 **Unhealthy** (laranja, healthcheck falhou)

---

### Operação 4: Inspecionar Configurações

**Cenário: Você quer ver a config completa de um container**

Via Terminal:
```bash
docker inspect ai-plane-api
```

Via Portainer:

1. **Containers** → Procure por **"ai-plane-api"**
2. Clique no nome do container
3. Você verá várias abas:

**Aba "General":**
- ID do container
- Status
- Imagem
- Porta e mapeamento de ports
- Rede

**Aba "Env":**
- Todas as variáveis de ambiente
- Exemplo:
  ```
  DATABASE_URL=postgresql://postgres:password@postgres-plane:5432/plane_db
  REDIS_URL=redis://plane-redis:6379/
  SECRET_KEY=xxxxx
  ```

**Aba "Volumes":**
- Volumes montados
- Exemplo:
  ```
  plane_data ↔ /app/data
  logs ↔ /code/plane/logs
  ```

**Aba "Network":**
- IP do container na rede `ai_net`
- Gateway
- Conexões com outros containers

---

## ✅ FASE 4: Validação e Boas Práticas

### Checklist de Validação

Use este checklist para garantir que a stack está sendo gerenciada corretamente:

```
[  ] Acessar Portainer em http://localhost:9000
[  ] Usuário admin criado com sucesso
[  ] Docker environment conectado e mostrando "Connected"
[  ] Stack "ai-stack" importada/criada
[  ] Todos os XX containers da stack visíveis
[  ] Número de containers corresponde ao esperado
[  ] Status dos containers:
    [  ] supabase-db: Running (Healthy)
    [  ] postgres-plane: Running (Healthy)
    [  ] ai-lightrag: Running (Healthy)
    [  ] ai-n8n: Running (Healthy)
    [  ] ai-neo4j: Running (Healthy)
    [  ] ai-openwebui: Running (Healthy)
    [  ] ai-plane-api: Running (Healthy)
    [  ] ai-plane-web: Running (Healthy)
    [  ] ai-portainer: Running (Healthy)
[  ] Acessar logs de pelo menos 1 container
[  ] Abrir Exec Console em supabase-db
[  ] Executar: psql -U supabase_admin -d postgres -c "\dt rag.*"
[  ] Ver 8 tabelas RAG retornadas
[  ] Acessar logs de ai-lightrag
[  ] Procurar por "Connected" ou "Started" nos logs
[  ] Acessar Exec Console em postgres-plane
[  ] Executar: psql -U postgres -l | grep plane_db
[  ] Ver plane_db listado
[  ] Inspecionar configuração de um container
[  ] Ver variáveis de ambiente corretas
[  ] Tentar Restart de um container não-crítico
[  ] Verificar que container reiniciou
[  ] Todas as abas funcionando (General, Env, Volumes, Network, Logs)
```

---

### Boas Práticas

#### 1. **Nunca Delete um Container da UI**

❌ **Não faça via Portainer:**
```
Clique em "Delete" para remover container
```

✅ **Faça via CLI se necessário:**
```bash
docker-compose down  # Controlado, previne erro
```

**Por quê?** Portainer não para dependências. Pode causar comportamento inesperado.

---

#### 2. **Use Stack Versioning**

Se precisar testar mudanças:

1. **Faça backup da stack atual:**
   - Nome: `ai-stack-backup-2025-11-02`
   - Copie o docker-compose.yml original

2. **Crie uma nova stack para testes:**
   - Nome: `ai-stack-dev`
   - Use o arquivo modificado

3. **Teste em `ai-stack-dev`**

4. **Depois promocione para `ai-stack`:**
   - Delete `ai-stack`
   - Renomeie `ai-stack-dev` para `ai-stack`

---

#### 3. **Monitore Healthchecks**

Portainer mostra status do healthcheck em cada container.

**Significado dos Status:**

```
🟢 Running (Green)
   └─ Healthcheck: Passing
   └─ Container está 100% operacional

🟡 Exited (Yellow)
   └─ Container crashou
   └─ Veja os logs para entender por quê

🔴 Stopped (Red)
   └─ Você parou manualmente
   └─ Clique "Start" para reiniciar

🟠 Unhealthy (Orange)
   └─ Container rodando mas healthcheck falhando
   └─ Exemplo: Porta 5432 não respondendo
   └─ Ação: Veja logs e reinicie
```

**Para Fazer Debug de Unhealthy:**

1. Vá para a aba **"Logs"**
2. Procure por erros recentes
3. Veja a configuração do healthcheck em **"General"**
4. Teste manualmente no **"Exec Console"**

---

#### 4. **Configurar Notificações (Opcional)**

Portainer pode avisar quando containers caem:

1. Vá para **"Settings"** → **"Notifications"**
2. Configure webhook para Discord/Slack (se desejado)
3. Defina regras para alertas

---

#### 5. **Limpeza Periódica**

Portainer pode acumular imagens, volumes e containers não usados:

1. Vá para **"System"** → **"System Information"**
2. Veja "Unused Images", "Unused Volumes", "Dangling"
3. Limpe periodicamente:
   ```
   Clique em "Prune" para remover recursos não-utilizados
   ```

---

## 🎓 Exemplos Práticos de Debugging

### Exemplo 1: LightRAG Não Conecta ao PostgreSQL

**Sintoma:** `ai-lightrag` está com status "Unhealthy"

**Debug via Portainer:**

1. Clique em **"ai-lightrag"** → **"Logs"**
2. Procure por mensagens de erro como:
   ```
   ERROR: could not connect to PostgreSQL
   ERROR: database "ai-stack" does not exist
   ERROR: role "supabase_admin" does not exist
   ```

3. Se vir "could not connect", verifique:
   - Abra **"Exec Console"** em `ai-lightrag`
   - Execute: `ping supabase-db`
   - Execute: `nc -zv supabase-db 5432`

4. Se DNS resolver mas porta não responder:
   - Vá para **"supabase-db"** → **"Logs"**
   - Verifique se PostgreSQL iniciou corretamente
   - Procure por "ready to accept connections"

5. Se PostgreSQL está ok, problema é na app:
   - Verifique variáveis de ambiente em **"Inspect"** → **"Env"**
   - Confirme: `POSTGRES_USER=supabase_admin`
   - Confirme: `POSTGRES_HOST=supabase-db`

---

### Exemplo 2: Plane não consegue criar tables

**Sintoma:** `ai-plane-api` mostra erros de permissão

**Debug via Portainer:**

1. Abra **"Exec Console"** em `postgres-plane`
2. Conecte ao banco:
   ```bash
   psql -U postgres -d plane_db
   ```

3. Verifique se plane_db existe:
   ```bash
   \l  # listar databases
   ```

4. Se plane_db não existe:
   ```bash
   # Saia do psql
   \q
   
   # Crie manualmente
   createdb -U postgres plane_db
   ```

5. Vá para **"ai-plane-api"** → Clique em **"Restart"**
6. Verifique logs novamente

---

### Exemplo 3: n8n Perdeu Dados

**Sintoma:** n8n não está mostrando workflows salvos

**Debug via Portainer:**

1. Vá para **"Volumes"** no menu esquerdo
2. Procure por `n8n_data`
3. Verifique:
   - Size (deve ser > 0MB)
   - Mount Point (deve estar mapeado corretamente)

4. Se volume está vazio, o problema é no mount:
   - Clique em **"ai-n8n"** → **"Inspect"**
   - Vá para **"Volumes"**
   - Verifique:
     ```
     n8n_data ↔ /home/node/.n8n
     ```

5. Se mount está correto mas volume vazio:
   - Restart n8n
   - Recrie workflows (infelizmente dados podem estar perdidos)

---

## 📊 Dashboard Customizado

Portainer permite criar dashboards personalizados:

### Criar Dashboard para AI-Stack

1. Vá para **"Dashboard"**
2. Clique em **"Custom Dashboard Settings"**
3. Adicione widgets úteis:

```
Widgets Recomendados:
├─ Resource Usage (CPU, Memory)
├─ Container Status (mostra running/stopped)
├─ Events (logs de ações recentes)
├─ Quick Access (botões para containers críticos)
└─ Health Status (resumo dos healthchecks)
```

4. Configure para mostrar apenas AI-Stack:
   - Filter by Stack: `ai-stack`

---

## 🚀 Workflow Recomendado

**Seu dia-a-dia com Portainer:**

```
1. Manhã:
   └─ Abrir http://localhost:9000
   └─ Verificar Dashboard
   └─ Confirmar que todos containers estão 🟢 Running

2. Durante Desenvolvimento:
   └─ Trabalhar em código
   └─ Precisar testar? Abrir Exec Console via Portainer
   └─ Fazer mudanças em docker-compose.yml?
       ├─ Delete a stack antiga
       ├─ Deploy nova versão
       └─ Portainer mostra novos containers automaticamente

3. Se Algo Quebra:
   └─ Abrir Logs do container afetado
   └─ Procurar pela mensagem de erro
   └─ Debugar com Exec Console
   └─ Reiniciar se necessário
   └─ Confirmar que saiu do erro

4. Manutenção Semanal:
   └─ Revisar Logs para warnings
   └─ Limpar imagens não-utilizadas
   └─ Fazer backup da stack config
   └─ Documenta mudanças
```

---

## 📞 Próximos Passos

1. ✅ **Acesse Portainer** em http://localhost:9000
2. ✅ **Crie usuário admin** com senha forte
3. ✅ **Importe sua AI-Stack** como Stack
4. ✅ **Execute o checklist de validação** acima
5. ✅ **Teste todas as operações** (Logs, Exec, Restart, etc)
6. ✅ **Familiarize-se com a UI** para debugging futuro

---

## 📋 Resumo: O Que Aprendeu

- ✅ Como acessar e configurar Portainer
- ✅ Como importar docker-compose.yml como Stack
- ✅ Como visualizar e gerenciar containers
- ✅ Como acessar logs em tempo real
- ✅ Como executar comandos dentro de containers (Exec)
- ✅ Como restartear/parar/iniciar serviços
- ✅ Como inspecionar configurações e variáveis
- ✅ Como debugar problemas comuns
- ✅ Boas práticas e workflow recomendado

**Agora você tem uma ferramenta profissional para gerenciar sua AI-Stack!** 🎉