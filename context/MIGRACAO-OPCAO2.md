# 🚀 GUIA DE MIGRAÇÃO: Opção 1 → Opção 2 (Banco Separado)

## ✅ Você Escolheu: OPÇÃO 2 (Modularizado)

Agora vamos implementar a arquitetura com PostgreSQL separado para Plane.

---

## 📋 O Que Vai Mudar

| Item | Antes (Opção 1) | Depois (Opção 2) |
|------|-----------------|------------------|
| **PostgreSQL Supabase** | 1 instância RAG + Plane | 1 instância RAG apenas |
| **PostgreSQL Plane** | ❌ Não existe | ✅ Novo: postgres-plane |
| **Conflito de usuários** | postgres vs supabase_admin | ✅ Resolvido! |
| **Desacoplamento** | Frágil | Robusto |
| **Porta PostgreSQL** | 5432 | supabase: 5432 + plane: 5433 |

---

## 🔧 FASE 1: Preparar Arquivos

### Passo 1: Fazer Backup

```bash
# Backup do docker-compose.yml atual
cp docker-compose.yml docker-compose.yml.backup-opcao1

# Backup de volumes (dados)
docker-compose down -v  # ⚠️  ISSO VAI LIMPAR DADOS!

# Se tiver dados importantes:
docker run --rm -v supabase_db_data:/data -v $(pwd)/backup:/backup \
  alpine tar czf /backup/supabase_db_data.tar.gz -C /data .
```

### Passo 2: Usar novo docker-compose.yml

```bash
# Remover arquivo antigo
rm docker-compose.yml

# Usar nova versão (Opção 2)
cp docker-compose-OPCAO2.yml docker-compose.yml

# Ou simplesmente renomear
mv docker-compose-OPCAO2.yml docker-compose.yml
```

### Passo 3: Verificar Mudanças-Chave

Abra `docker-compose.yml` e verifique:

```yaml
# ✅ NOVO: postgres-plane (linhas ~65-90)
postgres-plane:
  container_name: postgres-plane
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: plane_db
    POSTGRES_USER: postgres
  ports:
    - "5433:5432"  # ← Porta diferente!

# ✅ Supabase Healthcheck (linha ~140)
supabase-db:
  healthcheck:
    test: ["CMD", "pg_isready", "-U", "supabase_admin", "-h", "localhost"]  # ← Corrigido!

# ✅ LightRAG (linhas ~750+)
lightrag:
  environment:
    - POSTGRES_USER=supabase_admin  # ← Corrigido!
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# ✅ Plane API (linhas ~900+)
plane-api:
  environment:
    - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres-plane:5432/plane_db  # ← NOVO HOST!

# ✅ Plane Worker e Beat
plane-worker:
  environment:
    - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres-plane:5432/plane_db  # ← NOVO HOST!
```

---

## 🏗️ FASE 2: Inicializar Novos Serviços

### Passo 1: Limpar Volumes Antigos

```bash
# Se quer começar limpo:
docker-compose down -v

# Se quer manter dados do Supabase (RAG):
docker-compose down
```

### Passo 2: Levantar Apenas Bancos de Dados

```bash
# Iniciar o novo postgres-plane
docker-compose up -d postgres-plane

# Verificar que inicializou
docker-compose ps postgres-plane
# Esperado: ai-postgres-plane ... Healthy

# Aguardar ~10 segundos para health check passar
sleep 15
```

### Passo 3: Iniciar Supabase (RAG)

```bash
docker-compose up -d supabase-db

# Verificar
docker-compose ps supabase-db
# Esperado: supabase-db ... Healthy
```

### Passo 4: Verificar Logs de Inicialização

```bash
# Supabase RAG
docker logs supabase-db | grep -E "✅|Schema RAG|Triggers"

# PostgreSQL Plane
docker logs postgres-plane | grep "ready to accept"
```

---

## ✅ FASE 3: Validação Pós-Migração

### Teste 1: Verificar Supabase RAG

```bash
# Conectar ao supabase-db com supabase_admin
docker exec -i supabase-db psql -U supabase_admin -d postgres -c "\dt rag.*"

# Esperado: 8 tabelas listadas
```

### Teste 2: Verificar PostgreSQL Plane

```bash
# Conectar ao postgres-plane com postgres
docker exec -i postgres-plane psql -U postgres -d postgres -c "\l"

# Esperado: plane_db listado
```

### Teste 3: Verificar Conectividade entre Containers

```bash
# LightRAG consegue falar com Supabase?
docker exec -i ai-lightrag bash -c "curl -s http://supabase-db:5432" || echo "OK (conexão TCP)"

# Plane consegue falar com seu banco?
docker exec -i ai-plane-api bash -c "python -c \"import psycopg2; psycopg2.connect('postgresql://postgres:password@postgres-plane:5432/plane_db')\" && echo 'Plane OK'"
```

### Teste 4: Verificar Portas

```bash
# Listar portas abertas
docker-compose ps | grep -E "PORTS|postgres-plane|supabase-db"

# Esperado:
# postgres-plane         ... 5433->5432/tcp
# supabase-db            ... 5432->5432/tcp
```

---

## 🎯 FASE 4: Inicializar Serviços Dependentes

### Se Tudo OK, Levantar Toda a Stack

```bash
# Iniciar todo o docker-compose
docker-compose up -d

# Aguardar ~2 minutos enquanto tudo inicializa
sleep 120

# Verificar status
docker-compose ps

# Verificar logs de erro
docker-compose logs -t --tail=50 | grep -i "error\|fail"
```

---

## 📊 Checklist de Validação Final

```bash
#!/bin/bash
# Salve como: validate-opcao2.sh

echo "🔍 Validando OPÇÃO 2 (Banco Separado)..."
echo ""

# 1. Verificar containers rodando
echo "1️⃣  Containers rodando:"
docker-compose ps | grep -E "postgres-plane|supabase-db" | grep -i "healthy\|running"
echo ""

# 2. Verificar portas
echo "2️⃣  Portas configuradas:"
docker-compose ps | grep -E "postgres-plane|supabase-db" | awk '{print $1, $6}'
echo ""

# 3. Verificar Supabase RAG
echo "3️⃣  Schema RAG:"
docker exec -i supabase-db psql -U supabase_admin -d postgres -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='rag';" 2>/dev/null | tail -1
echo ""

# 4. Verificar Plane DB
echo "4️⃣  Plano DB criado:"
docker exec -i postgres-plane psql -U postgres -l 2>/dev/null | grep plane_db
echo ""

# 5. Verificar LightRAG
echo "5️⃣  LightRAG Status:"
docker logs ai-lightrag 2>&1 | grep -i "connected\|error" | tail -1
echo ""

# 6. Verificar Plane API
echo "6️⃣  Plane API Status:"
docker logs ai-plane-api 2>&1 | grep -i "started\|error" | tail -1
echo ""

echo "✅ Validação Completa!"
```

**Uso:**
```bash
chmod +x validate-opcao2.sh
./validate-opcao2.sh
```

---

## 🚨 Troubleshooting Comum

### Problema: "postgres-plane não inicia"

```bash
# Ver logs
docker logs postgres-plane

# Se houver erro de permissão:
docker-compose down -v postgres-plane
docker-compose up -d postgres-plane
```

### Problema: "Plane API não consegue conectar ao banco"

```bash
# Verificar se postgres-plane está healthy
docker-compose ps postgres-plane

# Testar conexão manualmente
docker exec -i postgres-plane psql -U postgres -d postgres -c "SELECT version();"

# Se falhar, verificar variável de ambiente em plane-api:
docker exec -i ai-plane-api env | grep DATABASE_URL
```

### Problema: "LightRAG falha ao conectar"

```bash
# Verifique se supabase_admin existe
docker exec -i supabase-db psql -U supabase_admin -d postgres -c "\du"

# Verifique se schema RAG existe
docker exec -i supabase-db psql -U supabase_admin -d postgres -c "\dn+ rag"

# Teste manualmente
docker exec -i supabase-db psql -U supabase_admin -d postgres -c "SELECT * FROM rag.sources LIMIT 1;"
```

### Problema: "Healthcheck falha para supabase-db"

```bash
# Verifique o healthcheck
docker-compose config | grep -A 8 "supabase-db:" | grep -A 5 "healthcheck"

# Deve estar com "supabase_admin", não "postgres"

# Se estiver com "postgres", atualize o arquivo docker-compose.yml
```

---

## 🎉 Próximos Passos (Após Validação)

1. ✅ **Stack rodando**: Todos containers healthy
2. ⏳ **Testar LightRAG**: Fazer INSERT no RAG schema
3. ⏳ **Testar Plane**: Acessar http://localhost:3002
4. ⏳ **Testar n8n**: Acessar http://localhost:5678
5. ⏳ **Testar OpenWebUI**: Acessar http://localhost:3001

---

## 📞 Rollback (Se Necessário)

Se precisar voltar para Opção 1:

```bash
# 1. Parar tudo
docker-compose down

# 2. Restaurar arquivo antigo
cp docker-compose.yml.backup-opcao1 docker-compose.yml

# 3. Levantar novamente
docker-compose up -d

# 4. Restaurar dados (se tiver backup)
docker run --rm -v supabase_db_data:/data -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/supabase_db_data.tar.gz -C /data
```

---

## 📝 Resumo das Mudanças

| Aspecto | Mudança |
|--------|---------|
| **Novo Container** | ✅ postgres-plane (padrão) |
| **Supabase Healthcheck** | ✅ postgres → supabase_admin |
| **LightRAG Usuario** | ✅ postgres → supabase_admin |
| **Plane Database URL** | ✅ Apontando para postgres-plane:5433 |
| **Desacoplamento** | ✅ Total |
| **Complexidade** | ⚠️ +1 container, -muitos problemas |

---

## ✨ Conclusão

**Antes (Opção 1):**
- ❌ 1 PostgreSQL compartilhado
- ❌ Conflito postgres vs supabase_admin
- ❌ Risco de quebra em atualizações
- ❌ Difícil debugar

**Depois (Opção 2):**
- ✅ 2 PostgreSQL independentes
- ✅ Sem conflito de usuários
- ✅ Seguro contra atualizações
- ✅ Fácil debugar
- ✅ Profissional e escalável

**Você acabou de implementar a melhor prática de microsserviços!** 🎉

---

Qualquer dúvida durante a migração, avise!