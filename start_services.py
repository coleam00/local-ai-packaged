#!/usr/bin/env python3
"""
start_services.py

This script starts the Supabase stack first, waits for it to initialize, and then starts
the local AI stack. Both stacks use the same Docker Compose project name ("localai")
so they appear together in Docker Desktop.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys
import json

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def load_stack_config():
    """Load stack configuration from .stack-config.json if it exists.

    This file is created by the Management UI wizard and contains:
    - profile: CPU/GPU selection
    - environment: private/public
    - enabled_services: list of services to start
    - port_overrides: custom port mappings

    Returns None if file doesn't exist or is invalid.
    """
    config_path = ".stack-config.json"
    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        print(f"Loaded stack configuration from {config_path}")
        print(f"  Profile: {config.get('profile', 'not set')}")
        print(f"  Environment: {config.get('environment', 'not set')}")
        print(f"  Enabled services: {len(config.get('enabled_services', []))} services")
        return config
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load {config_path}: {e}")
        return None

def cleanup_empty_db_directory():
    """Remove empty PostgreSQL data directory to allow proper initialization.

    If the directory exists but is empty, PostgreSQL thinks it's already
    initialized and skips running init scripts. We detect this case and
    remove the empty directory.
    """
    db_data_path = os.path.join("supabase", "docker", "volumes", "db", "data")

    if os.path.exists(db_data_path):
        # Check if directory is empty (only . and .. entries)
        try:
            entries = os.listdir(db_data_path)
            if not entries:  # Empty directory
                print(f"Removing empty PostgreSQL data directory: {db_data_path}")
                print("  (This allows PostgreSQL to properly initialize)")
                os.rmdir(db_data_path)
        except Exception as e:
            print(f"Warning: Could not check/remove {db_data_path}: {e}")

def ensure_supabase_directories():
    """Create required Supabase bind mount directories to prevent anonymous volumes.

    NOTE: We do NOT create db/data because PostgreSQL needs to detect it as
    non-existent to properly run initialization scripts. Creating an empty
    directory causes PostgreSQL to skip initialization.
    """
    print("Ensuring Supabase bind mount directories exist...")

    required_dirs = [
        # DO NOT include db/data - let PostgreSQL create it
        os.path.join("supabase", "docker", "volumes", "storage"),
        os.path.join("supabase", "docker", "volumes", "logs"),
    ]

    for dir_path in required_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"  Ensured: {dir_path}")

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

    # Ensure bind mount directories exist to prevent Docker from creating anonymous volumes
    ensure_supabase_directories()

def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)

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
    cmd = [
        "docker", "compose", "-p", "localai",
        "-f", "supabase/docker/docker-compose.yml",
    ]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)

def start_local_ai(profile=None, environment=None, enabled_services=None):
    """Start the local AI services (using its compose file).

    Args:
        profile: GPU profile (cpu, gpu-nvidia, gpu-amd, none)
        environment: Deployment environment (private, public)
        enabled_services: Optional list of specific services to start.
                         If None, starts all services for the profile.
    """
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

    # If specific services are requested, add them to the command
    # This tells docker compose to only start these services (plus their dependencies)
    if enabled_services:
        # Filter out Supabase services (they're started separately)
        supabase_services = {
            "db", "kong", "auth", "rest", "realtime", "storage", "imgproxy",
            "meta", "functions", "studio", "analytics", "vector", "supavisor"
        }
        local_ai_services = [s for s in enabled_services if s not in supabase_services]
        if local_ai_services:
            print(f"  Starting {len(local_ai_services)} selected services: {', '.join(local_ai_services)}")
            cmd.extend(local_ai_services)
        else:
            print("  No local AI services selected, skipping...")
            return

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
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default=None,
                      help='Profile to use for Docker Compose (default: from config or cpu)')
    parser.add_argument('--environment', choices=['private', 'public'], default=None,
                      help='Environment to use for Docker Compose (default: from config or private)')
    args = parser.parse_args()

    # Try to load configuration from wizard
    stack_config = load_stack_config()

    # Use config values if not overridden by CLI arguments
    profile = args.profile
    environment = args.environment
    enabled_services = None

    if stack_config:
        if profile is None:
            profile = stack_config.get("profile", "cpu")
        if environment is None:
            environment = stack_config.get("environment", "private")
        enabled_services = stack_config.get("enabled_services")
        print(f"\nUsing configuration from wizard:")
        print(f"  Profile: {profile}")
        print(f"  Environment: {environment}")
        if enabled_services:
            print(f"  Services: {len(enabled_services)} selected")
    else:
        # Defaults if no config file
        if profile is None:
            profile = "cpu"
        if environment is None:
            environment = "private"
        print(f"\nNo wizard configuration found, using defaults/CLI args:")
        print(f"  Profile: {profile}")
        print(f"  Environment: {environment}")
        print(f"  Services: all (no selection)")

    # Clean up empty db directory before starting (allows PostgreSQL to properly initialize)
    cleanup_empty_db_directory()

    clone_supabase_repo()
    prepare_supabase_env()

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    stop_existing_containers(profile)

    # Start Supabase first
    start_supabase(environment)

    # Give Supabase some time to initialize
    print("Waiting for Supabase to initialize...")
    time.sleep(10)

    # Then start the local AI services
    start_local_ai(profile, environment, enabled_services)

if __name__ == "__main__":
    main()
