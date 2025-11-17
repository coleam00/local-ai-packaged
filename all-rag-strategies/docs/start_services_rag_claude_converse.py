#!/usr/bin/env python3
"""
start_services.py

This script starts the Supabase stack first, waits for it to initialize, applies the RAG schema,
and then starts the local AI stack. Both stacks use the same Docker Compose project name ("localai")
so they appear together in Docker Desktop.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys
import asyncio
import asyncpg

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        run_command([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        os.chdir("supabase")
        run_command(["git", "pull"])
        os.chdir("..")

def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)

def prepare_rag_schema():
    """Copy RAG schema.sql to Supabase init directory for automatic execution."""
    print("Preparing RAG database schema...")
    
    # Paths
    schema_source = os.path.join("all-rag-strategies", "implementation", "sql", "schema.sql")
    supabase_init_dir = os.path.join("supabase", "docker", "volumes", "db", "init")
    schema_dest = os.path.join(supabase_init_dir, "02-rag-schema.sql")
    
    # Check if source schema exists
    if not os.path.exists(schema_source):
        print(f"WARNING: RAG schema file not found at {schema_source}")
        print("RAG functionality will not be available until schema is applied manually.")
        return False
    
    # Create init directory if it doesn't exist
    os.makedirs(supabase_init_dir, exist_ok=True)
    
    # Copy schema file
    try:
        shutil.copyfile(schema_source, schema_dest)
        print(f"✓ RAG schema copied to {schema_dest}")
        print("  Schema will be applied when Supabase database initializes")
        return True
    except Exception as e:
        print(f"ERROR: Failed to copy RAG schema: {e}")
        return False

async def wait_for_database(max_retries=30, retry_delay=2):
    """
    Wait for Supabase database to be ready and accepting connections.
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Seconds to wait between attempts
    
    Returns:
        bool: True if database is ready, False otherwise
    """
    from dotenv import load_dotenv
    load_dotenv(".env")
    
    # Get database credentials from environment
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    postgres_host = "localhost"  # We're connecting from host, not within Docker network
    postgres_port = "5432"
    postgres_db = "postgres"
    postgres_user = "postgres"
    
    if not postgres_password:
        print("ERROR: POSTGRES_PASSWORD not found in .env file")
        return False
    
    database_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    
    print(f"Waiting for Supabase database to be ready...")
    
    for attempt in range(1, max_retries + 1):
        try:
            # Attempt to connect
            conn = await asyncpg.connect(database_url, timeout=5)
            
            # Test connection with a simple query
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            
            if result == 1:
                print(f"✓ Database is ready (attempt {attempt}/{max_retries})")
                return True
                
        except (asyncpg.PostgresError, OSError, ConnectionRefusedError) as e:
            if attempt < max_retries:
                print(f"  Database not ready yet (attempt {attempt}/{max_retries}), retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"ERROR: Database failed to become ready after {max_retries} attempts")
                print(f"Last error: {e}")
                return False
    
    return False

async def verify_rag_schema():
    """
    Verify that RAG schema was applied successfully.
    
    Returns:
        bool: True if schema is present, False otherwise
    """
    from dotenv import load_dotenv
    load_dotenv(".env")
    
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    database_url = f"postgresql://postgres:{postgres_password}@localhost:5432/postgres"
    
    try:
        conn = await asyncpg.connect(database_url, timeout=10)
        
        # Check if documents table exists
        documents_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'documents')"
        )
        
        # Check if chunks table exists
        chunks_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'chunks')"
        )
        
        # Check if match_chunks function exists
        function_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM pg_proc WHERE proname = 'match_chunks')"
        )
        
        # Check if vector extension is enabled
        vector_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM pg_extension WHERE extname = 'vector')"
        )
        
        await conn.close()
        
        if documents_exists and chunks_exists and function_exists and vector_exists:
            print("✓ RAG schema verification successful:")
            print("  ✓ documents table present")
            print("  ✓ chunks table present")
            print("  ✓ match_chunks() function present")
            print("  ✓ pgvector extension enabled")
            return True
        else:
            print("⚠ RAG schema verification failed:")
            if not documents_exists:
                print("  ✗ documents table missing")
            if not chunks_exists:
                print("  ✗ chunks table missing")
            if not function_exists:
                print("  ✗ match_chunks() function missing")
            if not vector_exists:
                print("  ✗ pgvector extension not enabled")
            return False
            
    except Exception as e:
        print(f"ERROR: Schema verification failed: {e}")
        return False

async def initialize_rag_database():
    """
    Initialize RAG database schema after Supabase is ready.
    
    Returns:
        bool: True if initialization successful
    """
    print("\n" + "="*60)
    print("RAG Database Initialization")
    print("="*60)
    
    # Wait for database to be ready
    if not await wait_for_database():
        print("ERROR: Database initialization failed - Supabase database not ready")
        return False
    
    # Give database a moment to stabilize
    print("Database ready, waiting 3 seconds for stabilization...")
    await asyncio.sleep(3)
    
    # Verify schema was applied (should have been applied via init scripts)
    if await verify_rag_schema():
        print("✓ RAG database initialization complete")
        return True
    else:
        print("⚠ RAG schema not found - will need manual application")
        print("  Run: psql $DATABASE_URL < all-rag-strategies/implementation/sql/schema.sql")
        return False

def stop_existing_containers(profile=None):
    print("Stopping and removing existing containers for the unified project 'localai'...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "down"])
    run_command(cmd)

def start_supabase(environment=None):
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)

def start_local_ai(profile=None, environment=None):
    """Start the local AI services (using its compose file)."""
    print("Starting local AI services...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)

def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")

    # Define paths for SearXNG settings files
    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")

    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return

    # Check if settings.yml exists, if not create it from settings-base.yml
    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            shutil.copyfile(settings_base_path, settings_path)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return
    else:
        print(f"SearXNG settings.yml already exists at {settings_path}")

    print("Generating SearXNG secret key...")

    # Detect the platform and run the appropriate command
    system = platform.system()

    try:
        if system == "Windows":
            print("Detected Windows platform, using PowerShell to generate secret key...")
            # PowerShell command to generate a random key and replace in the settings file
            ps_command = [
                "powershell", "-Command",
                "$randomBytes = New-Object byte[] 32; " +
                "(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes); " +
                "$secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ }); " +
                "(Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml"
            ]
            subprocess.run(ps_command, check=True)

        elif system == "Darwin":  # macOS
            print("Detected macOS platform, using sed command with empty string parameter...")
            # macOS sed command requires an empty string for the -i parameter
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", "", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)

        else:  # Linux and other Unix-like systems
            print("Detected Linux/Unix platform, using standard sed command...")
            # Standard sed command for Linux
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)

        print("SearXNG secret key generated successfully.")

    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You may need to manually generate the secret key using the commands:")
        print("  - Linux: sed -i \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - macOS: sed -i '' \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - Windows (PowerShell):")
        print("    $randomBytes = New-Object byte[] 32")
        print("    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes)")
        print("    $secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ })")
        print("    (Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml")

def check_and_fix_docker_compose_for_searxng():
    """Check and modify docker-compose.yml for SearXNG first run."""
    docker_compose_path = "docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return

    try:
        # Read the docker-compose.yml file
        with open(docker_compose_path, 'r') as file:
            content = file.read()

        # Default to first run
        is_first_run = True

        # Check if Docker is running and if the SearXNG container exists
        try:
            # Check if the SearXNG container is running
            container_check = subprocess.run(
                ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            searxng_containers = container_check.stdout.strip().split('\n')

            # If SearXNG container is running, check inside for uwsgi.ini
            if any(container for container in searxng_containers if container):
                container_name = next(container for container in searxng_containers if container)
                print(f"Found running SearXNG container: {container_name}")

                # Check if uwsgi.ini exists inside the container
                container_check = subprocess.run(
                    ["docker", "exec", container_name, "sh", "-c", "[ -f /etc/searxng/uwsgi.ini ] && echo 'found' || echo 'not_found'"],
                    capture_output=True, text=True, check=False
                )

                if "found" in container_check.stdout:
                    print("Found uwsgi.ini inside the SearXNG container - not first run")
                    is_first_run = False
                else:
                    print("uwsgi.ini not found inside the SearXNG container - first run")
                    is_first_run = True
            else:
                print("No running SearXNG container found - assuming first run")
        except Exception as e:
            print(f"Error checking Docker container: {e} - assuming first run")

        if is_first_run and "cap_drop: - ALL" in content:
            print("First run detected for SearXNG. Temporarily removing 'cap_drop: - ALL' directive...")
            # Temporarily comment out the cap_drop line
            modified_content = content.replace("cap_drop: - ALL", "# cap_drop: - ALL  # Temporarily commented out for first run")

            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)

            print("Note: After the first run completes successfully, you should re-add 'cap_drop: - ALL' to docker-compose.yml for security reasons.")
        elif not is_first_run and "# cap_drop: - ALL  # Temporarily commented out for first run" in content:
            print("SearXNG has been initialized. Re-enabling 'cap_drop: - ALL' directive for security...")
            # Uncomment the cap_drop line
            modified_content = content.replace("# cap_drop: - ALL  # Temporarily commented out for first run", "cap_drop: - ALL")

            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)

    except Exception as e:
        print(f"Error checking/modifying docker-compose.yml for SearXNG: {e}")

def main():
    parser = argparse.ArgumentParser(description='Start the local AI and Supabase services.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Profile to use for Docker Compose (default: cpu)')
    parser.add_argument('--environment', choices=['private', 'public'], default='private',
                      help='Environment to use for Docker Compose (default: private)')
    parser.add_argument('--skip-rag-init', action='store_true',
                      help='Skip RAG database initialization (for testing)')
    args = parser.parse_args()

    clone_supabase_repo()
    prepare_supabase_env()
    
    # Prepare RAG schema before starting services
    prepare_rag_schema()

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    stop_existing_containers(args.profile)

    # Start Supabase first
    start_supabase(args.environment)

    # Initialize RAG database (wait for DB and verify schema)
    if not args.skip_rag_init:
        try:
            # Run async database initialization
            success = asyncio.run(initialize_rag_database())
            
            if not success:
                print("\n⚠ WARNING: RAG database initialization encountered issues")
                print("The system will continue, but RAG functionality may not work")
                print("You can manually apply the schema later with:")
                print("  psql $DATABASE_URL < all-rag-strategies/implementation/sql/schema.sql")
                print()
        except Exception as e:
            print(f"\nERROR: Failed to initialize RAG database: {e}")
            print("Continuing with service startup...\n")
    else:
        print("Skipping RAG database initialization (--skip-rag-init flag)")
        print("Waiting 10 seconds for Supabase to stabilize...")
        time.sleep(10)

    # Then start the local AI services
    start_local_ai(args.profile, args.environment)
    
    print("\n" + "="*60)
    print("✓ All services started successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Access n8n at http://localhost:5678")
    print("2. Access Open WebUI at http://localhost:3000")
    print("3. Access Supabase Studio at http://localhost:8005")
    print("\nTo ingest documents into the RAG system:")
    print("  docker compose -p localai --profile ingestion up")
    print("\nTo view logs:")
    print("  docker compose -p localai logs -f")
    print()

if __name__ == "__main__":
    main()
