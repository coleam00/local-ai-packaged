#!/usr/bin/env bash
# generate-env.sh — Generate .env from .env.tpl using 1Password CLI (Touch ID)
#
# Usage:
#   ./generate-env.sh          # Generate .env from .env.tpl
#   ./generate-env.sh --check  # Verify all op:// references resolve without writing .env
#
# Requires: 1Password CLI (op) with biometric unlock enabled.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL_FILE="$SCRIPT_DIR/.env.tpl"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ ! -f "$TPL_FILE" ]]; then
  echo "Error: .env.tpl not found at $TPL_FILE" >&2
  exit 1
fi

# Check 1Password CLI is installed
if ! command -v op &>/dev/null; then
  echo "Error: 1Password CLI (op) is not installed." >&2
  echo "Install: https://developer.1password.com/docs/cli/get-started/" >&2
  exit 1
fi

# --check mode: validate all op:// references resolve
if [[ "${1:-}" == "--check" ]]; then
  echo "Checking all op:// references in .env.tpl..."
  errors=0
  while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$line" ]] && continue
    # Extract {{ op://... }} references
    if [[ "$line" =~ \{\{[[:space:]]*(op://[^}]+[^[:space:]])[[:space:]]*\}\} ]]; then
      ref="${BASH_REMATCH[1]}"
      var_name="${line%%=*}"
      if op read "$ref" &>/dev/null; then
        echo "  OK: $var_name → $ref"
      else
        echo "  FAIL: $var_name → $ref" >&2
        ((errors++))
      fi
    fi
  done < "$TPL_FILE"

  if [[ $errors -gt 0 ]]; then
    echo ""
    echo "$errors reference(s) failed. Fix them in 1Password before generating .env." >&2
    exit 1
  else
    echo ""
    echo "All references resolved successfully."
    exit 0
  fi
fi

# Generate .env by injecting secrets via op
echo "Generating .env from .env.tpl via 1Password (Touch ID)..."
op inject -i "$TPL_FILE" -o "$ENV_FILE" --force

# Restrict permissions
chmod 600 "$ENV_FILE"

echo "Generated $ENV_FILE (permissions: 600)"
echo "Secrets pulled from 1Password vault 'Local AI Packaged'."
