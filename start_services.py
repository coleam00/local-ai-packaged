#!/usr/bin/env python3
"""
start_services.py

This script can operate in two modes:

1. Default mode: Clones Supabase repository, sets up configuration, and manages both 
   Supabase and local AI services together.

2. External Supabase mode (--ext-supabase): Uses an existing Supabase installation
   at the specified path. Will not modify the existing Supabase configuration.

Both modes use the same Docker Compose project name ("localai") so all services 
appear together in Docker Desktop.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys

def run_command(cmd, cwd=None, suppress_orphan_warning=False, quiet=False):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    
    if quiet or suppress_orphan_warning:
        # Capture all output
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        
        if quiet:
            # Only show summary lines for docker compose up/down
            if 'up' in cmd or 'down' in cmd:
                stdout_lines = result.stdout.split('\n')
                for line in stdout_lines:
                    # Show network and summary lines, skip verbose container status
                    if (line.strip() and 
                        ('Network' in line or 'Running' in line or 'Container' in line) and
                        ('Creating' not in line and 'Created' not in line and 'Starting' not in line and 
                         'Started' not in line and 'Waiting' not in line and 'Healthy' not in line)):
                        print(line)
            else:
                # For non-docker-compose commands, show all output
                if result.stdout:
                    print(result.stdout, end='')
        else:
            # Show stdout normally
            if result.stdout:
                print(result.stdout, end='')
        
        # Handle stderr (with orphan warning filtering if requested)
        if result.stderr:
            stderr_lines = result.stderr.split('\n')
            for line in stderr_lines:
                if suppress_orphan_warning and 'Found orphan containers' in line:
                    continue
                if line.strip():
                    print(line, file=sys.stderr)
        
        # Check return code
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd)
    else:
        subprocess.run(cmd, cwd=cwd, check=True)

def check_external_supabase(supabase_path):
    """Check if external Supabase installation exists and is properly configured."""
    if not os.path.exists(supabase_path):
        print(f"Error: External Supabase installation not found at {supabase_path}")
        sys.exit(1)
    
    docker_compose_path = os.path.join(supabase_path, "docker-compose.yml")
    if not os.path.exists(docker_compose_path):
        print(f"Error: Supabase docker-compose.yml not found at {docker_compose_path}")
        sys.exit(1)
    
    env_path = os.path.join(supabase_path, ".env")
    if not os.path.exists(env_path):
        print(f"Error: Supabase .env file not found at {env_path}")
        sys.exit(1)
    
    print(f"Found external Supabase installation at {supabase_path}")
    return supabase_path

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


def stop_existing_containers(profile=None):
    print("Stopping and removing existing local AI containers...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "down"])
    run_command(cmd)

def stop_internal_supabase_containers():
    """Stop containers for internal Supabase (cloned repo)."""
    print("Stopping and removing existing internal Supabase containers...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml", "down"]
    run_command(cmd)

def stop_external_supabase_containers(supabase_path):
    """Stop containers for external Supabase installation."""
    print("Stopping and removing existing external Supabase containers...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "docker-compose.yml", "down"]
    run_command(cmd, cwd=supabase_path)

def start_internal_supabase(environment=None):
    """Start the Supabase services (using cloned repository)."""
    print("Starting internal Supabase services...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)

def start_external_supabase(supabase_path, environment=None):
    """Start the Supabase services (using external compose file)."""
    print("Starting external Supabase services...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "docker-compose.yml"]
    if environment and environment == "public":
        # Look for override file in the current local-ai directory
        override_path = os.path.join(os.getcwd(), "docker-compose.override.public.supabase.yml")
        if os.path.exists(override_path):
            cmd.extend(["-f", override_path])
    cmd.extend(["up", "-d"])
    run_command(cmd, cwd=supabase_path)

def start_local_ai(profile=None, environment=None, suppress_orphan_warning=False, quiet=False):
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
    run_command(cmd, suppress_orphan_warning=suppress_orphan_warning, quiet=quiet)

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
    parser.add_argument('--ext-supabase', type=str, metavar='PATH',
                      help='Path to external Supabase installation (enables external mode)')
    args = parser.parse_args()

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()
    
    # Stop existing containers first
    stop_existing_containers(args.profile)
    
    if args.ext_supabase:
        # External Supabase mode
        supabase_path = os.path.abspath(args.ext_supabase)
        check_external_supabase(supabase_path)
        
        # Stop external Supabase containers
        stop_external_supabase_containers(supabase_path)
        
        # Start external Supabase first
        start_external_supabase(supabase_path, args.environment)
        
        # Give Supabase some time to initialize
        print("Waiting for Supabase to initialize...")
        time.sleep(10)
        
        # Start local AI services (suppress orphan warning and use quiet mode for external mode)
        start_local_ai(args.profile, args.environment, suppress_orphan_warning=True, quiet=True)
        
    else:
        # Internal Supabase mode (original behavior)
        
        # Safety check: warn if external Supabase containers are running
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=supabase-", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            running_supabase = [name for name in result.stdout.strip().split('\n') if name.strip()]
            if running_supabase:
                print("\n⚠️  WARNING: Detected running Supabase containers from external installation:")
                for container in running_supabase:
                    print(f"   - {container}")
                print("\nIf you intended to use external Supabase, add --ext-supabase PATH")
                print("Continue with internal Supabase setup? (y/N): ", end="")
                response = input().strip().lower()
                if response not in ['y', 'yes']:
                    print("Aborting. Use --ext-supabase PATH for external Supabase mode.")
                    sys.exit(1)
        except Exception:
            pass  # Ignore errors in safety check
        
        clone_supabase_repo()
        prepare_supabase_env()
        
        # Stop internal Supabase containers
        stop_internal_supabase_containers()
        
        # Start internal Supabase first
        start_internal_supabase(args.environment)
        
        # Give Supabase some time to initialize
        print("Waiting for Supabase to initialize...")
        time.sleep(10)
        
        # Start local AI services (no need to suppress orphan warning for internal mode)
        start_local_ai(args.profile, args.environment)

if __name__ == "__main__":
    main()
