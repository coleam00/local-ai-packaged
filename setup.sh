#!/bin/bash
# =============================================================================
# Local AI Packaged - Automated Setup Script
# Target: Mac with native Ollama | Profile: none | Environment: private
# =============================================================================
set -e

echo ""
echo "=============================="
echo " Phase 1: Prerequisites"
echo "=============================="
echo ""

# 1.1 Check Docker
if ! command -v docker &>/dev/null; then
  echo "ERROR: Docker is not installed."
  echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
  echo "Then re-run this script."
  exit 1
fi
echo "Docker found: $(docker --version)"

# 1.2 Start Docker Desktop
open -a Docker 2>/dev/null || true
echo "Waiting for Docker to start..."
for i in $(seq 1 30); do
  docker info &>/dev/null && echo "Docker is ready!" && break
  [ "$i" -eq 30 ] && echo "ERROR: Docker did not start in time." && exit 1
  sleep 2
done

# 1.3 Check Python 3
if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3 is not installed."
  exit 1
fi
echo "Python found: $(python3 --version)"

# 1.4 Check Git
if ! command -v git &>/dev/null; then
  echo "ERROR: Git is not installed."
  exit 1
fi
echo "Git found: $(git --version)"

echo ""
echo "=============================="
echo " Phase 2: Clone & Configure"
echo "=============================="
echo ""

# 2.1 Clone repository
if [ ! -d "$HOME/local-ai-packaged" ]; then
  git clone -b stable https://github.com/coleam00/local-ai-packaged.git "$HOME/local-ai-packaged"
else
  echo "Repository already exists at ~/local-ai-packaged"
fi
cd "$HOME/local-ai-packaged"

# 2.2 Create .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from template"
else
  echo ".env already exists, skipping"
fi

# 2.3 Generate secrets
python3 -c "
import hmac, hashlib, base64, json, time, subprocess, os

def rand_hex(n=32):
    return subprocess.check_output(['openssl', 'rand', '-hex', str(n)]).decode().strip()

def make_jwt(secret, role):
    def b64url(data):
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()
    header = b64url(json.dumps({'alg':'HS256','typ':'JWT'}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({'role': role, 'iss': 'supabase', 'iat': now, 'exp': now + 157680000}).encode())
    sig = b64url(hmac.new(secret.encode(), f'{header}.{payload}'.encode(), hashlib.sha256).digest())
    return f'{header}.{payload}.{sig}'

secrets = {
    'N8N_ENCRYPTION_KEY': rand_hex(),
    'N8N_USER_MANAGEMENT_JWT_SECRET': rand_hex(),
    'POSTGRES_PASSWORD': rand_hex(24),
    'JWT_SECRET': rand_hex(),
    'DASHBOARD_PASSWORD': rand_hex(16),
    'POOLER_TENANT_ID': '1000',
    'NEO4J_AUTH': 'neo4j/' + rand_hex(16),
    'CLICKHOUSE_PASSWORD': rand_hex(),
    'MINIO_ROOT_PASSWORD': rand_hex(),
    'LANGFUSE_SALT': rand_hex(),
    'NEXTAUTH_SECRET': rand_hex(),
    'ENCRYPTION_KEY': rand_hex(),
    'SECRET_KEY_BASE': rand_hex(32),
    'VAULT_ENC_KEY': rand_hex(16),
    'LOGFLARE_PUBLIC_ACCESS_TOKEN': rand_hex(24),
    'LOGFLARE_PRIVATE_ACCESS_TOKEN': rand_hex(24),
}
secrets['ANON_KEY'] = make_jwt(secrets['JWT_SECRET'], 'anon')
secrets['SERVICE_ROLE_KEY'] = make_jwt(secrets['JWT_SECRET'], 'service_role')

with open('.env', 'r') as f: content = f.read()

replacements = {
    'N8N_ENCRYPTION_KEY=super-secret-key': f\"N8N_ENCRYPTION_KEY={secrets['N8N_ENCRYPTION_KEY']}\",
    'N8N_USER_MANAGEMENT_JWT_SECRET=even-more-secret': f\"N8N_USER_MANAGEMENT_JWT_SECRET={secrets['N8N_USER_MANAGEMENT_JWT_SECRET']}\",
    'POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password': f\"POSTGRES_PASSWORD={secrets['POSTGRES_PASSWORD']}\",
    'JWT_SECRET=your-super-secret-jwt-token-with-at-least-32-characters-long': f\"JWT_SECRET={secrets['JWT_SECRET']}\",
    'ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJhbm9uIiwKICAgICJpc3MiOiAic3VwYWJhc2UtZGVtbyIsCiAgICAiaWF0IjogMTY0MTc2OTIwMCwKICAgICJleHAiOiAxNzk5NTM1NjAwCn0.dc_X5iR_VP_qT0zsiyj_I_OZ2T9FtRU2BBNWN8Bu4GE': f\"ANON_KEY={secrets['ANON_KEY']}\",
    'SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJzZXJ2aWNlX3JvbGUiLAogICAgImlzcyI6ICJzdXBhYmFzZS1kZW1vIiwKICAgICJpYXQiOiAxNjQxNzY5MjAwLAogICAgImV4cCI6IDE3OTk1MzU2MDAKfQ.DaYlNEoUrrEn2Ig7tqibS-PHK5vgusbcbo7X36XVt4Q': f\"SERVICE_ROLE_KEY={secrets['SERVICE_ROLE_KEY']}\",
    'DASHBOARD_PASSWORD=this_password_is_insecure_and_should_be_updated': f\"DASHBOARD_PASSWORD={secrets['DASHBOARD_PASSWORD']}\",
    'POOLER_TENANT_ID=your-tenant-id': f\"POOLER_TENANT_ID={secrets['POOLER_TENANT_ID']}\",
    'NEO4J_AUTH=neo4j/password': f\"NEO4J_AUTH={secrets['NEO4J_AUTH']}\",
    'CLICKHOUSE_PASSWORD=super-secret-key-1': f\"CLICKHOUSE_PASSWORD={secrets['CLICKHOUSE_PASSWORD']}\",
    'MINIO_ROOT_PASSWORD=super-secret-key-2': f\"MINIO_ROOT_PASSWORD={secrets['MINIO_ROOT_PASSWORD']}\",
    'LANGFUSE_SALT=super-secret-key-3': f\"LANGFUSE_SALT={secrets['LANGFUSE_SALT']}\",
    'NEXTAUTH_SECRET=super-secret-key-4': f\"NEXTAUTH_SECRET={secrets['NEXTAUTH_SECRET']}\",
    'ENCRYPTION_KEY=generate-with-openssl': f\"ENCRYPTION_KEY={secrets['ENCRYPTION_KEY']}\",
    'SECRET_KEY_BASE=UpNVntn3cDxHJpq99YMc1T1AQgQpc8kfYTuRgBiYa15BLrx8etQoXz3gZv1/u2oq': f\"SECRET_KEY_BASE={secrets['SECRET_KEY_BASE']}\",
    'VAULT_ENC_KEY=your-32-character-encryption-key': f\"VAULT_ENC_KEY={secrets['VAULT_ENC_KEY']}\",
    'LOGFLARE_PUBLIC_ACCESS_TOKEN=your-super-secret-and-long-logflare-key-public': f\"LOGFLARE_PUBLIC_ACCESS_TOKEN={secrets['LOGFLARE_PUBLIC_ACCESS_TOKEN']}\",
    'LOGFLARE_PRIVATE_ACCESS_TOKEN=your-super-secret-and-long-logflare-key-private': f\"LOGFLARE_PRIVATE_ACCESS_TOKEN={secrets['LOGFLARE_PRIVATE_ACCESS_TOKEN']}\",
}

for old, new in replacements.items(): content = content.replace(old, new)

with open('.env', 'w') as f: f.write(content)

print('All secrets generated and written to .env')
print(f\"  Neo4j credentials: {secrets['NEO4J_AUTH']}\")
print('  (save these somewhere safe)')
"

# 2.4 Fix Langfuse NEXTAUTH_URL
sed -i '' 's|NEXTAUTH_URL: http://localhost:3002|NEXTAUTH_URL: http://localhost:3000|g' docker-compose.yml

echo ""
echo "=============================="
echo " Phase 3: Ollama & Models"
echo "=============================="
echo ""

# 3.1 Install Ollama
if ! command -v ollama &>/dev/null; then
  echo "Installing Ollama via Homebrew..."
  brew install ollama
else
  echo "Ollama already installed: $(ollama --version)"
fi

# 3.2 Start Ollama
if ! curl -sf http://localhost:11434 &>/dev/null; then
  echo "Starting Ollama..."
  ollama serve &>/dev/null &
  sleep 3
fi
echo "Ollama is running"

# 3.3 Pull models
echo "Pulling AI models (this may take several minutes)..."
OLLAMA_MODEL="${OLLAMA_MODEL:-$(sed -n 's/^OLLAMA_MODEL=//p' .env | tail -n 1)}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
echo "Pulling chat model: $OLLAMA_MODEL"
ollama pull "$OLLAMA_MODEL"
ollama pull nomic-embed-text

echo ""
echo "=============================="
echo " Phase 4: Launch Stack"
echo "=============================="
echo ""

# 4.1 Start services
cd "$HOME/local-ai-packaged"
python3 start_services.py --profile none --environment private

# 4.2 Wait for services
echo ""
echo "Waiting for services to become healthy..."

for svc in "n8n:5678/healthz" "Open WebUI:8080" "Qdrant:6333/healthz" "Langfuse:3000"; do
  name="${svc%%:*}"
  endpoint="${svc#*:}"
  for i in $(seq 1 30); do
    curl -sf "http://localhost:$endpoint" &>/dev/null && echo "$name is ready" && break
    [ "$i" -eq 30 ] && echo "WARNING: $name may not be ready yet"
    sleep 4
  done
done

echo ""
echo "All core services are up!"

# 4.3 Show container status
echo ""
docker compose -p localai -f docker-compose.yml ps

echo ""
echo "=============================="
echo " AUTOMATED SETUP COMPLETE"
echo "=============================="
echo ""
echo "Now complete the manual steps in your browser:"
echo ""
echo "  1. n8n          -> http://localhost:5678   (create owner account)"
echo "  2. Open WebUI   -> http://localhost:8080   (create admin, set Ollama URL to http://host.docker.internal:11434)"
echo "  3. Neo4j        -> http://localhost:7474   (log in with NEO4J_AUTH credentials)"
echo "  4. Langfuse     -> http://localhost:3000   (create account + project)"
echo "  5. Test it!     -> http://localhost:8080   (send a chat message)"
echo ""

# Open all service UIs in browser tabs
open http://localhost:5678
sleep 1
open http://localhost:8080
sleep 1
open http://localhost:7474
sleep 1
open http://localhost:3000
