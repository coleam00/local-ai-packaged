#!/usr/bin/env python3
import os
import subprocess
import argparse

def run_docker_command(command):
    """Execute a docker command and return its output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        print(result.stdout)
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def get_import_directories():
    """Get the base import directory."""
    # Get the project root directory (parent of 'scripts')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Set import base directory
    import_base = os.path.join(project_root, 'n8n', 'backup', 'import')
    workflows_dir = os.path.join(import_base, 'workflows')
    credentials_dir = os.path.join(import_base, 'credentials')
    
    return import_base, workflows_dir, credentials_dir

def import_workflows(workflows_dir):
    """Import workflows from specified directory."""
    if not os.path.exists(workflows_dir):
        print(f"Workflow directory does not exist: {workflows_dir}")
        return False
    
    workflow_files = [f for f in os.listdir(workflows_dir) if f.endswith('.json')]
    
    if not workflow_files:
        print(f"No workflow JSON files found in {workflows_dir}")
        return False
    
    print(f"Found {len(workflow_files)} workflow files to import:")
    for workflow in workflow_files:
        print(f"  - {workflow}")
    
    # Ensure the import directory exists in the container
    create_dir_command = 'docker exec n8n mkdir -p /backup/import/workflows'
    if not run_docker_command(create_dir_command):
        print("Failed to create import directory in container")
        return False
    
    # Copy files to container
    for workflow in workflow_files:
        src_path = os.path.join(workflows_dir, workflow)
        copy_command = f'docker cp "{src_path}" n8n:/backup/import/workflows/'
        if not run_docker_command(copy_command):
            print(f"Failed to copy workflow file: {workflow}")
            return False
    
    # Import workflows
    import_command = 'docker exec n8n n8n import:workflow --separate --input=/backup/import/workflows'
    return run_docker_command(import_command)

def import_credentials(credentials_dir):
    """Import credentials from specified directory."""
    if not os.path.exists(credentials_dir):
        print(f"Credentials directory does not exist: {credentials_dir}")
        return False
    
    credential_files = [f for f in os.listdir(credentials_dir) if f.endswith('.json')]
    
    if not credential_files:
        print(f"No credential JSON files found in {credentials_dir}")
        return False
    
    print(f"Found {len(credential_files)} credential files to import:")
    for credential in credential_files:
        print(f"  - {credential}")
    
    # Ensure the import directory exists in the container
    create_dir_command = 'docker exec n8n mkdir -p /backup/import/credentials'
    if not run_docker_command(create_dir_command):
        print("Failed to create import directory in container")
        return False
    
    # Copy files to container
    for credential in credential_files:
        src_path = os.path.join(credentials_dir, credential)
        copy_command = f'docker cp "{src_path}" n8n:/backup/import/credentials/'
        if not run_docker_command(copy_command):
            print(f"Failed to copy credential file: {credential}")
            return False
    
    # Import credentials
    import_command = 'docker exec n8n n8n import:credentials --separate --input=/backup/import/credentials'
    return run_docker_command(import_command)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Import N8N workflows and credentials')
    parser.add_argument('-w', '--workflows', action='store_true', help='Import only workflows')
    parser.add_argument('-c', '--credentials', action='store_true', help='Import only credentials')
    args = parser.parse_args()
    
    # Get import directories
    import_base, workflows_dir, credentials_dir = get_import_directories()
    
    # Determine what to import
    import_all = not (args.workflows or args.credentials)
    
    # Perform import
    success = True
    if import_all or args.workflows:
        success &= import_workflows(workflows_dir)
    
    if import_all or args.credentials:
        success &= import_credentials(credentials_dir)
    
    # Final status
    if success:
        print("\nImport completed successfully!")
    else:
        print("\nImport encountered some issues.")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()