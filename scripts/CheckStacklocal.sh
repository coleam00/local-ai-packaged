#!/bin/bash
set -e

echo "🔍 LocalAI Container Network & Service Diagnostic"
echo "================================================"
echo ""

echo "📡 Container IP Address:"
ip a | grep -A 2 "inet " | grep -v "inet6" | awk '{print " -", $2}'
echo ""

echo "📦 Docker Containers Running:"
docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"
echo ""

echo "🧠 Listening Ports on Host (ss -tulpn):"
ss -tulpn | grep LISTEN
echo ""

echo "🚦 Testing Service Ports with curl..."
declare -A services
services=(
  [WebUI]=3000
  [n8n]=5678
  [Flowise]=3001
  [Langfuse]=3002
  [Qdrant]=6333
  [Neo4j]=7474
  [SearXNG]=8080
  [Supabase API]=8000
  [Ollama]=11434
)

for name in "${!services[@]}"; do
  port=${services[$name]}
  echo -n "🔗 $name (http://localhost:$port): "
  if curl -s --connect-timeout 2 http://localhost:$port >/dev/null; then
    echo "✅ reachable"
  else
    echo "❌ unreachable"
  fi
done

echo ""
echo "✅ Diagnostic complete. If any services are unreachable, verify Docker container port bindings and .env configuration."
