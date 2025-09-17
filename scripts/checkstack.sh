#!/usr/bin/env bash
set -euo pipefail

HOST_IP=${HOST_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}
echo "Host IP: $HOST_IP"
echo

echo "=== Container Status ==="
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | sort
echo

# Map friendly names -> container name -> expected public port(s)
declare -A MAP=(
  [openwebui]=open-webui
  [flowise]=flowise
  [n8n]=n8n
  [langfuse]=localai-langfuse-web-1
  [qdrant]=qdrant
  [clickhouse]=localai-clickhouse-1
  [neo4j]=localai-neo4j-1
  [searxng]=searxng
  [ollama]=ollama
)

# curl a URL and print code (000 if connection fails)
curl_code () { curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$1" || echo 000; }

printf "=== HTTP Checks ===\n%-12s %-8s %s\n" "Service" "Code" "URL"
echo "------------ -------- -------------------------"

for svc in "${!MAP[@]}"; do
  cname="${MAP[$svc]}"
  ports=$(docker ps --filter "name=^/${cname}$" --format '{{.Ports}}')

  # pick a reasonable HTTP port to test based on service
  case "$svc" in
    openwebui)   port=$(sed -n 's/.*:\([0-9]\+\)->8080.*/\1/p' <<<"$ports"); path=/ ;;
    flowise)     port=$(sed -n 's/.*:\([0-9]\+\)->3001.*/\1/p' <<<"$ports"); path=/ ;;
    n8n)         port=$(sed -n 's/.*:\([0-9]\+\)->5678.*/\1/p' <<<"$ports"); path=/ ;;
    langfuse)    port=$(sed -n 's/.*:\([0-9]\+\)->3000.*/\1/p' <<<"$ports"); path=/ ;;
    qdrant)      port=$(sed -n 's/.*:\([0-9]\+\)->6333.*/\1/p' <<<"$ports"); path=/ ;;
    clickhouse)  port=$(sed -n 's/.*:\([0-9]\+\)->8123.*/\1/p' <<<"$ports"); path=/ping ;;
    neo4j)       port=$(sed -n 's/.*:\([0-9]\+\)->7474.*/\1/p' <<<"$ports"); path=/ ;;
    searxng)     port=$(sed -n 's/.*:\([0-9]\+\)->8080.*/\1/p' <<<"$ports"); path=/ ;;
    ollama)      port=$(sed -n 's/.*:\([0-9]\+\)->11434.*/\1/p'<<<"$ports"); path=/api/tags ;;
  esac

  if [[ -n "${port:-}" ]]; then
    url="http://${HOST_IP}:${port}${path}"
    code=$(curl_code "$url")
    printf "%-12s %-8s %s\n" "$svc" "$code" "$url"
  else
    printf "%-12s %-8s %s\n" "$svc" "N/A" "(no published port found)"
  fi
done

echo
echo "Tip: If a service shows N/A, it’s only exposed internally (Traefik/Caddy can still reach it)."