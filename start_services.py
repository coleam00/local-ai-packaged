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
import stat
import secrets
import tempfile

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def command_works(cmd):
    """Return True if a command can be executed successfully."""
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def detect_runtime_and_compose():
    """
    Detect runtime and compose command.
    Priority:
      1) CONTAINER_RUNTIME=docker|podman
      2) podman compose
      3) docker compose
    """
    requested = os.getenv("CONTAINER_RUNTIME", "").strip().lower()
    if requested:
        if requested not in {"docker", "podman"}:
            raise RuntimeError("CONTAINER_RUNTIME must be either 'docker' or 'podman'")
        compose_cmd = [requested, "compose"]
        if not command_works(compose_cmd + ["version"]):
            raise RuntimeError(f"Requested runtime '{requested}' is not usable ({' '.join(compose_cmd)} version failed)")
        return requested, compose_cmd

    if shutil.which("podman") and command_works(["podman", "compose", "version"]):
        return "podman", ["podman", "compose"]

    if shutil.which("docker") and command_works(["docker", "compose", "version"]):
        return "docker", ["docker", "compose"]

    raise RuntimeError("Could not find a usable container runtime. Install podman or docker with compose support.")


def is_unix_socket(path):
    """Return True when path exists and is a Unix socket."""
    if not path:
        return False
    try:
        st = os.stat(path)
    except OSError:
        return False
    return stat.S_ISSOCK(st.st_mode)


def detect_socket_location(runtime):
    """
    Detect the host container socket path used by vector/log collector.
    For podman rootless, this usually lives at /run/user/<uid>/podman/podman.sock.
    """
    env_socket = os.getenv("DOCKER_SOCKET_LOCATION", "").strip()

    if runtime == "docker":
        candidates = [env_socket, "/var/run/docker.sock", "/run/docker.sock"]
    else:
        uid = os.getuid()
        candidates = [
            env_socket,
            f"/run/user/{uid}/podman/podman.sock",
            "/run/podman/podman.sock",
            "/var/run/podman/podman.sock",
            "/var/run/docker.sock",
            "/run/docker.sock",
        ]

    for candidate in candidates:
        if is_unix_socket(candidate):
            return candidate

    return env_socket if env_socket else None


def ensure_podman_socket():
    """Best-effort: start the podman user socket if systemd user services are available."""
    if not shutil.which("systemctl"):
        return
    try:
        subprocess.run(
            ["systemctl", "--user", "start", "podman.socket"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        # Non-fatal: we keep fallback behavior and print warning later.
        pass


def set_env_value(path, key, value):
    """Set or append KEY=value in a dotenv file."""
    lines = []
    found = False
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(f"{key}="):
                lines.append(f"{key}={value}\n")
                found = True
            else:
                lines.append(line)
    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        lines.append(f"{key}={value}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

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

def fix_windows_line_endings():
    """Fix CRLF line endings in Supabase config files on Windows."""
    if platform.system() != "Windows":
        return
    
    pooler_path = os.path.join("supabase", "docker", "volumes", "pooler", "pooler.exs")
    if not os.path.exists(pooler_path):
        return
    
    print("Fixing Windows line endings in pooler.exs...")
    try:
        with open(pooler_path, 'rb') as f:
            content = f.read()
        content = content.replace(b'\r\n', b'\n')
        with open(pooler_path, 'wb') as f:
            f.write(content)
        print("Fixed line endings in pooler.exs")
    except Exception as e:
        print(f"Warning: Could not fix line endings in pooler.exs: {e}")

def prepare_supabase_env(runtime):
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)

    socket_location = detect_socket_location(runtime)
    if runtime == "podman" and not socket_location:
        ensure_podman_socket()
        socket_location = detect_socket_location(runtime)
    if socket_location:
        print(f"Using container socket location: {socket_location}")
        set_env_value(env_path, "DOCKER_SOCKET_LOCATION", socket_location)
    else:
        print("Warning: Could not detect a container socket path. Keeping DOCKER_SOCKET_LOCATION as-is.")

def stop_existing_containers(compose_cmd, profile=None, compose_file="docker-compose.yml"):
    print("Stopping and removing existing containers for the unified project 'localai'...")
    cmd = compose_cmd + ["-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", compose_file, "down"])
    run_command(cmd)

def start_supabase(compose_cmd, environment=None):
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    cmd = compose_cmd + ["-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)

def start_local_ai(compose_cmd, profile=None, environment=None, compose_file="docker-compose.yml"):
    """Start the local AI services (using its compose file)."""
    print("Starting local AI services...")
    cmd = compose_cmd + ["-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", compose_file])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)


def compose_includes_supabase():
    """Return True when docker-compose.yml already includes Supabase compose file."""
    compose_path = "docker-compose.yml"
    if not os.path.exists(compose_path):
        return False
    try:
        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()
        return "./supabase/docker/docker-compose.yml" in content
    except Exception:
        return False


def build_compose_without_include(source_path):
    """
    Create a temporary compose file without top-level `include:`.
    This avoids relative-path issues in podman-compose when included files are used.
    """
    with open(source_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("include:"):
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith(" ") or nxt.startswith("\t") or nxt.strip() == "":
                    i += 1
                    continue
                break
            continue
        out.append(line)
        i += 1

    fd, path = tempfile.mkstemp(prefix="localai-no-include-", suffix=".yml", dir=".")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)
    return path

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

    try:
        random_key = secrets.token_hex(32)
        with open(settings_path, "r", encoding="utf-8") as f:
            content = f.read()
        updated = content.replace("ultrasecretkey", random_key)
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(updated)
        print("SearXNG secret key generated successfully.")

    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You may need to manually set the secret key in searxng/settings.yml.")

def check_and_fix_docker_compose_for_searxng(container_cli):
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

        # Check if runtime is running and if the SearXNG container exists
        try:
            # Check if the SearXNG container is running
            container_check = subprocess.run(
                [container_cli, "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            searxng_containers = container_check.stdout.strip().split('\n')

            # If SearXNG container is running, check inside for uwsgi.ini
            if any(container for container in searxng_containers if container):
                container_name = next(container for container in searxng_containers if container)
                print(f"Found running SearXNG container: {container_name}")

                # Check if uwsgi.ini exists inside the container
                container_check = subprocess.run(
                    [container_cli, "exec", container_name, "sh", "-c", "[ -f /etc/searxng/uwsgi.ini ] && echo 'found' || echo 'not_found'"],
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
    args = parser.parse_args()
    runtime, compose_cmd = detect_runtime_and_compose()
    print(f"Using container runtime: {runtime}")
    local_ai_compose_file = "docker-compose.yml"
    if runtime == "podman" and compose_includes_supabase():
        local_ai_compose_file = build_compose_without_include("docker-compose.yml")
        print(f"Using podman-safe compose file: {local_ai_compose_file}")

    clone_supabase_repo()
    fix_windows_line_endings()
    prepare_supabase_env(runtime)

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng(runtime)

    stop_existing_containers(compose_cmd, args.profile, local_ai_compose_file)

    # Start Supabase first
    start_supabase(compose_cmd, args.environment)

    # Give Supabase some time to initialize
    print("Waiting for Supabase to initialize...")
    time.sleep(10)

    # Then start the local AI services
    start_local_ai(compose_cmd, args.profile, args.environment, local_ai_compose_file)

if __name__ == "__main__":
    main()
