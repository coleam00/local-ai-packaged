#!/usr/bin/env bash
# docker-mcp-gateway.sh — start Docker Desktop's MCP Toolkit gateway as an HTTP-streamable
# endpoint so n8n's "MCP Client Tool" node can call any of the configured MCP servers.
#
# Usage:
#   ./scripts/docker-mcp-gateway.sh               # foreground, port 8811
#   ./scripts/docker-mcp-gateway.sh --port 9000   # custom port
#   PROFILE=default ./scripts/docker-mcp-gateway.sh
#
# Auth: a stable token is read from ~/.docker/mcp-gateway-token (created on first run).
# Pass that token to the n8n MCP Client Tool node's HTTP Bearer Auth credential.

set -euo pipefail

PORT="${PORT:-8811}"
PROFILE="${PROFILE:-default}"
TOKEN_FILE="${HOME}/.docker/mcp-gateway-token"

# Parse --port if supplied
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# Ensure stable token
if [[ ! -f "$TOKEN_FILE" ]]; then
  mkdir -p "$(dirname "$TOKEN_FILE")"
  openssl rand -hex 32 > "$TOKEN_FILE"
  chmod 600 "$TOKEN_FILE"
  echo "Generated new gateway token at $TOKEN_FILE"
fi

export MCP_GATEWAY_AUTH_TOKEN
MCP_GATEWAY_AUTH_TOKEN="$(cat "$TOKEN_FILE")"

echo "→ Starting Docker MCP gateway"
echo "  Profile : $PROFILE"
echo "  URL     : http://localhost:${PORT}/mcp"
echo "  Token   : (in $TOKEN_FILE — chmod 600)"
echo "  From n8n: http://host.docker.internal:${PORT}/mcp"
echo ""

exec docker mcp gateway run \
  --transport streaming \
  --port "$PORT" \
  --profile "$PROFILE" \
  --log-calls
