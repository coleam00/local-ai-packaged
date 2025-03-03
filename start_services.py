#!/usr/bin/env python3
"""
start_services.py

This script starts the Supabase stack first, waits for it to initialize, and then starts
the local AI stack. Both stacks use the same Docker Compose project name ("localai")
so they appear together in Docker Desktop.

Enhanced version with better error handling and network management.
"""

import os
import subprocess
import shutil
import time
import argparse
import sys
from typing import List, Optional

def run_command(cmd: List[str], cwd: Optional[str] = None, capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    try:
        return subprocess.run(cmd, cwd=cwd, check=True, capture_output=capture_output, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(cmd)}")
        print(f"Error output: {e.stderr if hasattr(e, 'stderr') else 'No error output available'}")
        raise

def clone_supabase_repo() -> None:
    """Clone the Supabase repository using sparse checkout if not already present."""
    max_retries = 3
    retry_delay = 5  # seconds

    def git_command_with_retry(cmd: List[str], cwd: Optional[str] = None) -> None:
        for attempt in range(max_retries):
            try:
                # Add git config commands to handle SSL issues
                if cmd[0] == "git" and cmd[1] == "pull":
                    # First try to set SSL verification to false
                    subprocess.run(["git", "config", "--global", "http.sslVerify", "false"], 
                                 check=True, capture_output=True)
                
                result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
                # Reset SSL verification to true after successful pull
                if cmd[0] == "git" and cmd[1] == "pull":
                    subprocess.run(["git", "config", "--global", "http.sslVerify", "true"],
                                 check=True, capture_output=True)
                return
            except subprocess.CalledProcessError as e:
                print(f"Attempt {attempt + 1} failed: {e.stderr}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    # If all retries failed but supabase directory exists, continue anyway
                    if os.path.exists("supabase") and os.path.exists(os.path.join("supabase", "docker")):
                        print("Git operation failed but required files exist. Continuing...")
                        return
                    print("All retry attempts failed.")
                    raise

    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        git_command_with_retry([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        os.chdir("supabase")
        git_command_with_retry(["git", "sparse-checkout", "init", "--cone"])
        git_command_with_retry(["git", "sparse-checkout", "set", "docker"])
        git_command_with_retry(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        os.chdir("supabase")
        git_command_with_retry(["git", "pull"])
        os.chdir("..")

def remove_network(network_name: str) -> None:
    """Remove Docker network if it exists."""
    try:
        subprocess.run(
            ["docker", "network", "rm", network_name],
            check=True,
            capture_output=True
        )
        print(f"Removed network {network_name}")
        # Wait a bit for the network to be fully removed
        time.sleep(2)
    except subprocess.CalledProcessError:
        pass  # Ignore if network doesn't exist

def clean_docker_environment() -> None:
    """Clean up Docker environment completely."""
    print("Cleaning up Docker environment...")
    
    # Stop all running containers in the project
    try:
        run_command([
            "docker", "compose",
            "-p", "localai",
            "-f", "docker-compose.yml",
            "-f", "supabase/docker/docker-compose.yml",
            "down", "--remove-orphans"
        ])
    except Exception as e:
        print(f"Warning: Error during compose down: {str(e)}")
    
    # Force remove all containers with the project name
    try:
        containers = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "name=localai"],
            capture_output=True, text=True, check=True
        ).stdout.strip().split('\n')
        
        for container in containers:
            if container:  # Skip empty strings
                try:
                    subprocess.run(["docker", "rm", "-f", container], check=True)
                except Exception as e:
                    print(f"Warning: Could not remove container {container}: {str(e)}")
    except Exception as e:
        print(f"Warning: Error listing containers: {str(e)}")
    
    # Remove all networks related to the project
    try:
        networks = subprocess.run(
            ["docker", "network", "ls", "--filter", "name=localai", "--format", "{{.ID}}"],
            capture_output=True, text=True, check=True
        ).stdout.strip().split('\n')
        
        for network in networks:
            if network:  # Skip empty strings
                try:
                    subprocess.run(["docker", "network", "rm", "-f", network], check=True)
                except Exception as e:
                    print(f"Warning: Could not remove network {network}: {str(e)}")
    except Exception as e:
        print(f"Warning: Error listing networks: {str(e)}")
    
    # Remove the specific network
    remove_network("localai_default")
    
    # Prune networks
    run_command(["docker", "network", "prune", "-f"])
    
    # Wait longer for everything to clean up
    print("Waiting for Docker resources to clean up...")
    time.sleep(10)  # Increased wait time to ensure complete cleanup
    time.sleep(3)

def prepare_supabase_env() -> None:
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    
    if not os.path.exists(env_example_path):
        print("Error: .env file not found in root directory")
        sys.exit(1)
        
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)

def start_supabase() -> None:
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    compose_file = os.path.join("supabase", "docker", "docker-compose.yml")
    if not os.path.exists(compose_file):
        raise FileNotFoundError(f"Docker compose file not found: {compose_file}")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            run_command([
                "docker", "compose", "-p", "localai", "-f", compose_file, "up", "-d"
            ])
            print("Supabase services started successfully")
            return
        except subprocess.CalledProcessError as e:
            print(f"Attempt {attempt + 1} failed to start Supabase services")
            if attempt < max_retries - 1:
                print("Cleaning up and retrying...")
                clean_docker_environment()
                time.sleep(5)
            else:
                raise Exception("Failed to start Supabase services after multiple attempts")

def start_local_ai(profile: Optional[str] = None) -> None:
    """Start the local AI services (using its compose file)."""
    print("Starting local AI services...")
    
    # Prepare the command
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "up", "-d"])
    
    # Add retry logic
    max_retries = 3
    current_retry = 0
    
    while current_retry < max_retries:
        try:
            run_command(cmd)
            print("Local AI services started successfully")
            break
        except subprocess.CalledProcessError as e:
            current_retry += 1
            print(f"Attempt {current_retry} failed. Error: {str(e)}")
            if current_retry < max_retries:
                print(f"Waiting 10 seconds before retry {current_retry + 1}/{max_retries}...")
                time.sleep(10)
            else:
                raise Exception("Failed to start local AI services after multiple attempts")

def check_prerequisites() -> None:
    """Check if all prerequisites are met."""
    try:
        # Check Docker
        run_command(["docker", "--version"], capture_output=True)
        # Check Docker Compose
        run_command(["docker", "compose", "version"], capture_output=True)
        # Check Git
        run_command(["git", "--version"], capture_output=True)
    except subprocess.CalledProcessError as e:
        print("Error: Prerequisites check failed")
        print(f"Error details: {str(e)}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: Required program not found: {str(e)}")
        print("Please ensure Docker, Docker Compose, and Git are installed and in your PATH")
        sys.exit(1)

def main() -> None:
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Start the local AI and Supabase services.')
    parser.add_argument('--profile', 
                       choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], 
                       default='cpu',
                       help='Profile to use for Docker Compose (default: cpu)')
    args = parser.parse_args()

    try:
        # Check prerequisites first
        check_prerequisites()
        
        # Initialize services
        clone_supabase_repo()
        prepare_supabase_env()
        
        # Clean up Docker environment completely
        clean_docker_environment()
        
        # Start Supabase first
        start_supabase()
        
        # Give Supabase some time to initialize
        print("Waiting for Supabase to initialize...")
        time.sleep(15)  # Increased wait time
        
        # Then start the local AI services
        start_local_ai(args.profile)
        
        print("\nAll services started successfully!")
        print("You can access:")
        print("- n8n at: http://localhost:5678")
        print("- Open WebUI at: http://localhost:3000")
        print("- Supabase Studio at: http://localhost:8000")
        print("- Flowise at: http://localhost:3001")
        print("- Qdrant Dashboard at: http://localhost:6333")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()