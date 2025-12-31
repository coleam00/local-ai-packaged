import secrets
import jwt
from datetime import datetime
from typing import Dict

def generate_hex_key(bytes_length: int = 32) -> str:
    """Generate a random hex key."""
    return secrets.token_hex(bytes_length)

def generate_safe_password(length: int = 24) -> str:
    """Generate a secure password without problematic characters."""
    # Only use alphanumeric and a few safe special chars
    # Avoid: @ % = + # $ ! ^ & * (shell expansion, env parsing, URL encoding issues)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
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

        # Management UI
        "MANAGEMENT_SECRET_KEY": generate_hex_key(32),

        # Flowise (optional but recommended for security)
        "FLOWISE_USERNAME": "admin",
        "FLOWISE_PASSWORD": generate_safe_password(16),
    }

def get_required_defaults() -> Dict[str, str]:
    """Get required configuration defaults (non-secret values).

    These are values that Supabase docker-compose.yml requires but are not secrets.
    Without these, services like analytics won't know how to connect to the database.
    """
    return {
        # Database connection (required for analytics, etc.)
        "POSTGRES_HOST": "db",
        "POSTGRES_DB": "postgres",
        "POSTGRES_PORT": "5432",

        # Docker socket location
        "DOCKER_SOCKET_LOCATION": "/var/run/docker.sock",

        # Supabase pooler settings
        "POOLER_PROXY_PORT_TRANSACTION": "6543",
        "POOLER_DEFAULT_POOL_SIZE": "20",
        "POOLER_MAX_CLIENT_CONN": "100",
        "POOLER_DB_POOL_SIZE": "5",

        # Kong ports
        "KONG_HTTP_PORT": "8000",
        "KONG_HTTPS_PORT": "8443",

        # PostgREST
        "PGRST_DB_SCHEMAS": "public,storage,graphql_public",

        # Auth defaults
        "SITE_URL": "http://localhost:3000",
        "API_EXTERNAL_URL": "http://localhost:8000",
        "ADDITIONAL_REDIRECT_URLS": "",
        "JWT_EXPIRY": "3600",
        "DISABLE_SIGNUP": "false",
        "ENABLE_EMAIL_SIGNUP": "true",
        "ENABLE_EMAIL_AUTOCONFIRM": "true",
        "ENABLE_PHONE_SIGNUP": "true",
        "ENABLE_PHONE_AUTOCONFIRM": "true",
        "ENABLE_ANONYMOUS_USERS": "false",

        # SMTP defaults (local mail container)
        "SMTP_ADMIN_EMAIL": "admin@example.com",
        "SMTP_HOST": "supabase-mail",
        "SMTP_PORT": "2500",
        "SMTP_USER": "fake_mail_user",
        "SMTP_PASS": "fake_mail_password",
        "SMTP_SENDER_NAME": "fake_sender",

        # Mailer paths
        "MAILER_URLPATHS_CONFIRMATION": "/auth/v1/verify",
        "MAILER_URLPATHS_INVITE": "/auth/v1/verify",
        "MAILER_URLPATHS_RECOVERY": "/auth/v1/verify",
        "MAILER_URLPATHS_EMAIL_CHANGE": "/auth/v1/verify",

        # Studio
        "STUDIO_DEFAULT_ORGANIZATION": "Default Organization",
        "STUDIO_DEFAULT_PROJECT": "Default Project",
        "SUPABASE_PUBLIC_URL": "http://localhost:8000",
        "IMGPROXY_ENABLE_WEBP_DETECTION": "true",

        # Functions
        "FUNCTIONS_VERIFY_JWT": "false",
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


def apply_required_defaults(current_env: Dict[str, str]) -> Dict[str, str]:
    """Apply required defaults only if they're missing from the env."""
    defaults = get_required_defaults()
    result = {}

    for key, default_value in defaults.items():
        if key not in current_env or not current_env[key]:
            result[key] = default_value

    return result
