import secrets
import jwt
from datetime import datetime
from typing import Dict

def generate_hex_key(bytes_length: int = 32) -> str:
    """Generate a random hex key."""
    return secrets.token_hex(bytes_length)

def generate_safe_password(length: int = 24) -> str:
    """Generate a secure password without problematic characters."""
    # Avoid @, %, =, +, and other chars that can cause issues in .env files and connection strings
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$^&*-_"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_supabase_jwt(role: str, jwt_secret: str) -> str:
    """Generate Supabase JWT key (anon or service_role)."""
    payload = {
        "role": role,
        "iss": "supabase-local",
        "iat": int(datetime.now().timestamp()),
        "exp": int(datetime(2099, 12, 31).timestamp())
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")

def generate_all_secrets() -> Dict[str, str]:
    """Generate all required secrets for the stack."""
    jwt_secret = generate_hex_key(32)

    return {
        # n8n
        "N8N_ENCRYPTION_KEY": generate_hex_key(32),
        "N8N_USER_MANAGEMENT_JWT_SECRET": generate_hex_key(32),

        # Supabase core
        "POSTGRES_PASSWORD": generate_safe_password(24),
        "JWT_SECRET": jwt_secret,
        "ANON_KEY": generate_supabase_jwt("anon", jwt_secret),
        "SERVICE_ROLE_KEY": generate_supabase_jwt("service_role", jwt_secret),
        "SECRET_KEY_BASE": generate_hex_key(32),
        "VAULT_ENC_KEY": generate_safe_password(32),
        "PG_META_CRYPTO_KEY": generate_safe_password(32),

        # Supabase dashboard
        "DASHBOARD_USERNAME": "admin",
        "DASHBOARD_PASSWORD": generate_safe_password(16),

        # Supabase pooler
        "POOLER_TENANT_ID": f"tenant-{secrets.token_hex(8)}",

        # Neo4j
        "NEO4J_AUTH": f"neo4j/{generate_safe_password(16)}",

        # Langfuse
        "CLICKHOUSE_PASSWORD": generate_safe_password(20),
        "MINIO_ROOT_PASSWORD": generate_safe_password(20),
        "LANGFUSE_SALT": generate_hex_key(16),
        "NEXTAUTH_SECRET": generate_hex_key(32),
        "ENCRYPTION_KEY": generate_hex_key(32),

        # Logflare
        "LOGFLARE_PUBLIC_ACCESS_TOKEN": generate_hex_key(32),
        "LOGFLARE_PRIVATE_ACCESS_TOKEN": generate_hex_key(32),
    }

def generate_missing_secrets(current_env: Dict[str, str]) -> Dict[str, str]:
    """Generate only the secrets that are missing or have placeholder values."""
    all_secrets = generate_all_secrets()
    result = {}

    placeholders = ["secret", "password", "your-", "change", "example", "super-secret"]

    for key, new_value in all_secrets.items():
        current_value = current_env.get(key, "")

        # Generate if missing or is a placeholder
        is_placeholder = any(p in current_value.lower() for p in placeholders) if current_value else True

        if not current_value or is_placeholder:
            result[key] = new_value

    return result
