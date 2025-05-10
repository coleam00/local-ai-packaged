#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime

def run_docker_command(command):
    """Execute a docker command and return its output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def create_backup_directory():
    """Create backup directory if it doesn't exist."""
    # Get the project root directory (parent of 'scripts')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    backup_base = os.path.join(project_root, 'n8n', 'backup')
    workflows_dir = os.path.join(backup_base, 'workflows')
    credentials_dir = os.path.join(backup_base, 'credentials')
    
    os.makedirs(workflows_dir, exist_ok=True)
    os.makedirs(credentials_dir, exist_ok=True)
    
    return backup_base

def get_user_choice():
    """Display menu and get user's backup choice."""
    print("N8N Backup Options:")
    print("1. Backup Workflows")
    print("2. Backup Credentials")
    print("3. Backup Both Workflows and Credentials")
    
    while True:
        try:
            choice = input("Enter your choice (1/2/3): ").strip()
            if choice in ['1', '2', '3']:
                return choice
            print("Invalid choice. Please enter 1, 2, or 3.")
        except KeyboardInterrupt:
            print("\nBackup cancelled.")
            exit(0)

def confirm_sensitive_export():
    """Warn user about sensitive data in credentials export."""
    print("\n" + "="*70)
    print("WARNING: SENSITIVE DATA EXPORT")
    print("="*70)
    print("You are about to export credentials which may contain:")
    print("- API Keys")
    print("- Passwords")
    print("- Authentication Tokens")
    print("\nTHESE ARE HIGHLY SENSITIVE PIECES OF INFORMATION!")
    print("\nSafety Recommendations:")
    print("1. Store exported files in a secure, encrypted location")
    print("2. Do NOT share these files publicly")
    print("3. Delete files when no longer needed")
    print("="*70)
    
    while True:
        response = input("\nAre you ABSOLUTELY SURE you want to proceed? (yes/no): ").strip().lower()
        if response == 'yes':
            return True
        elif response == 'no':
            print("Credential export cancelled.")
            return False
        else:
            print("Please respond with 'yes' or 'no'.")

def backup_workflows(backup_base, timestamp):
    """Backup n8n workflows."""
    workflows_dir = os.path.join(backup_base, 'workflows')
    command = f'docker exec n8n sh -c "n8n export:workflow --backup --output=/backup/workflows/{timestamp}"'
    if run_docker_command(command):
        # Copy from docker container to local filesystem
        copy_command = f'docker cp n8n:/backup/workflows/{timestamp} {workflows_dir}'
        if run_docker_command(copy_command):
            print(f"Workflows backed up to {workflows_dir}/{timestamp}")
            return True
    return False

def backup_credentials(backup_base, timestamp):
    """Backup n8n credentials."""
    # Confirm sensitive export
    if not confirm_sensitive_export():
        return False
    
    credentials_dir = os.path.join(backup_base, 'credentials')
    command = f'docker exec n8n sh -c "n8n export:credentials --backup --output=/backup/credentials/{timestamp}"'
    if run_docker_command(command):
        # Copy from docker container to local filesystem
        copy_command = f'docker cp n8n:/backup/credentials/{timestamp} {credentials_dir}'
        if run_docker_command(copy_command):
            print(f"Credentials backed up to {credentials_dir}/{timestamp}")
            return True
    return False

def main():
    # Create backup directories
    backup_base = create_backup_directory()
    
    # Get timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Get user's choice
    choice = get_user_choice()
    
    # Perform backup based on choice
    if choice == '1':
        backup_workflows(backup_base, timestamp)
    elif choice == '2':
        backup_credentials(backup_base, timestamp)
    elif choice == '3':
        backup_workflows(backup_base, timestamp)
        backup_credentials(backup_base, timestamp)
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()