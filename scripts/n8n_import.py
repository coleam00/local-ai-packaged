#!/usr/bin/env python3
"""
n8n Workflow Import/Export Tool

Imports and exports n8n workflows via REST API.
Replaces the n8n-import Docker container.

Usage:
    python scripts/n8n_import.py import    # Import workflows from backup
    python scripts/n8n_import.py export    # Export workflows to backup
    python scripts/n8n_import.py list      # List workflows in n8n
"""

import argparse
import json
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' module not found. Install with: pip install requests")
    sys.exit(1)

# Constants
DEFAULT_N8N_URL = "http://localhost:5678"
SCRIPT_DIR = Path(__file__).parent
BACKUP_DIR = SCRIPT_DIR.parent / "n8n" / "backup" / "workflows"
DEFAULT_TIMEOUT = 60
RETRY_DELAY = 2


def wait_for_n8n(base_url: str, timeout: int) -> bool:
    """Wait for n8n to be healthy.

    Args:
        base_url: n8n base URL
        timeout: Maximum seconds to wait

    Returns:
        True if n8n is healthy, False if timeout
    """
    print(f"Waiting for n8n to be ready (timeout: {timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/healthz", timeout=5)
            if response.status_code == 200:
                print("n8n is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        elapsed = int(time.time() - start_time)
        print(f"  Waiting... ({elapsed}s)", end="\r")
        time.sleep(RETRY_DELAY)

    print(f"\nTimeout: n8n not ready after {timeout}s")
    return False


def get_workflows(base_url: str) -> list:
    """Get all workflows from n8n.

    Args:
        base_url: n8n base URL

    Returns:
        List of workflow dictionaries
    """
    response = requests.get(f"{base_url}/api/v1/workflows")
    response.raise_for_status()
    return response.json().get("data", [])


def find_workflow_by_name(base_url: str, name: str) -> dict | None:
    """Find a workflow by name.

    Args:
        base_url: n8n base URL
        name: Workflow name to find

    Returns:
        Workflow dict if found, None otherwise
    """
    workflows = get_workflows(base_url)
    for workflow in workflows:
        if workflow.get("name") == name:
            return workflow
    return None


def import_workflow(base_url: str, workflow_data: dict) -> tuple[bool, str]:
    """Import a single workflow (create or update).

    Args:
        base_url: n8n base URL
        workflow_data: Workflow JSON data

    Returns:
        Tuple of (success, message)
    """
    name = workflow_data.get("name", "Unknown")

    # Check if workflow already exists
    existing = find_workflow_by_name(base_url, name)

    # Remove fields that shouldn't be in the import payload
    payload = {k: v for k, v in workflow_data.items()
               if k not in ["id", "createdAt", "updatedAt"]}

    try:
        if existing:
            # Update existing workflow
            workflow_id = existing["id"]
            response = requests.put(
                f"{base_url}/api/v1/workflows/{workflow_id}",
                json=payload
            )
            response.raise_for_status()
            return True, f"Updated: {name}"
        else:
            # Create new workflow
            response = requests.post(
                f"{base_url}/api/v1/workflows",
                json=payload
            )
            response.raise_for_status()
            return True, f"Created: {name}"
    except requests.exceptions.HTTPError as e:
        return False, f"Failed: {name} - {e}"


def export_workflow(base_url: str, workflow_id: str, output_path: Path) -> tuple[bool, str]:
    """Export a single workflow to file.

    Args:
        base_url: n8n base URL
        workflow_id: Workflow ID to export
        output_path: Path to save the workflow JSON

    Returns:
        Tuple of (success, message)
    """
    try:
        response = requests.get(f"{base_url}/api/v1/workflows/{workflow_id}")
        response.raise_for_status()
        workflow = response.json()

        # Write to file with pretty formatting
        with open(output_path, "w") as f:
            json.dump(workflow, f, indent=2)

        return True, f"Exported: {workflow.get('name', 'Unknown')} -> {output_path.name}"
    except requests.exceptions.HTTPError as e:
        return False, f"Failed to export {workflow_id}: {e}"
    except IOError as e:
        return False, f"Failed to write {output_path}: {e}"


def import_all(base_url: str, backup_dir: Path, specific_file: Path = None) -> tuple[int, int]:
    """Import all workflows from backup directory.

    Args:
        base_url: n8n base URL
        backup_dir: Directory containing workflow JSON files
        specific_file: If provided, only import this file

    Returns:
        Tuple of (success_count, fail_count)
    """
    success_count = 0
    fail_count = 0

    if specific_file:
        files = [specific_file]
    else:
        if not backup_dir.exists():
            print(f"Error: Backup directory not found: {backup_dir}")
            return 0, 0
        files = list(backup_dir.glob("*.json"))

    if not files:
        print("No workflow files found to import.")
        return 0, 0

    print(f"Importing {len(files)} workflow(s)...")

    for filepath in files:
        try:
            with open(filepath) as f:
                workflow_data = json.load(f)

            success, message = import_workflow(base_url, workflow_data)
            print(f"  {message}")

            if success:
                success_count += 1
            else:
                fail_count += 1

        except json.JSONDecodeError as e:
            print(f"  Failed: {filepath.name} - Invalid JSON: {e}")
            fail_count += 1
        except IOError as e:
            print(f"  Failed: {filepath.name} - {e}")
            fail_count += 1

    return success_count, fail_count


def export_all(base_url: str, backup_dir: Path) -> tuple[int, int]:
    """Export all workflows to backup directory.

    Args:
        base_url: n8n base URL
        backup_dir: Directory to save workflow JSON files

    Returns:
        Tuple of (success_count, fail_count)
    """
    success_count = 0
    fail_count = 0

    # Ensure backup directory exists
    backup_dir.mkdir(parents=True, exist_ok=True)

    workflows = get_workflows(base_url)

    if not workflows:
        print("No workflows found to export.")
        return 0, 0

    print(f"Exporting {len(workflows)} workflow(s)...")

    for workflow in workflows:
        workflow_id = workflow["id"]
        name = workflow.get("name", f"workflow_{workflow_id}")
        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
        output_path = backup_dir / f"{safe_name}.json"

        success, message = export_workflow(base_url, workflow_id, output_path)
        print(f"  {message}")

        if success:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count


def list_workflows(base_url: str) -> None:
    """List all workflows in n8n.

    Args:
        base_url: n8n base URL
    """
    workflows = get_workflows(base_url)

    if not workflows:
        print("No workflows found.")
        return

    print(f"Found {len(workflows)} workflow(s):\n")
    print(f"{'ID':<30} {'Name':<50} {'Active':<8}")
    print("-" * 90)

    for workflow in workflows:
        workflow_id = workflow.get("id", "N/A")
        name = workflow.get("name", "Unnamed")
        active = "Yes" if workflow.get("active") else "No"

        # Truncate long names
        if len(name) > 48:
            name = name[:45] + "..."

        print(f"{workflow_id:<30} {name:<50} {active:<8}")


def main():
    parser = argparse.ArgumentParser(
        description="Import/export n8n workflows via REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/n8n_import.py import              # Import all workflows
  python scripts/n8n_import.py export              # Export all workflows
  python scripts/n8n_import.py list                # List all workflows
  python scripts/n8n_import.py import --file workflow.json
  python scripts/n8n_import.py import --url http://n8n.example.com:5678
        """
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Import command
    import_parser = subparsers.add_parser("import", help="Import workflows from backup")
    import_parser.add_argument(
        "--file",
        type=Path,
        help="Import specific workflow file instead of all"
    )
    import_parser.add_argument(
        "--url",
        default=DEFAULT_N8N_URL,
        help=f"n8n URL (default: {DEFAULT_N8N_URL})"
    )
    import_parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Health check timeout in seconds (default: {DEFAULT_TIMEOUT})"
    )
    import_parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Skip waiting for n8n to be ready"
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export workflows to backup")
    export_parser.add_argument(
        "--url",
        default=DEFAULT_N8N_URL,
        help=f"n8n URL (default: {DEFAULT_N8N_URL})"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List workflows in n8n")
    list_parser.add_argument(
        "--url",
        default=DEFAULT_N8N_URL,
        help=f"n8n URL (default: {DEFAULT_N8N_URL})"
    )

    args = parser.parse_args()

    try:
        if args.command == "import":
            # Wait for n8n unless --no-wait
            if not args.no_wait:
                if not wait_for_n8n(args.url, args.timeout):
                    print("Error: n8n is not available. Use --no-wait to skip health check.")
                    sys.exit(1)

            success, fail = import_all(args.url, BACKUP_DIR, args.file)
            print(f"\nImport complete: {success} succeeded, {fail} failed")
            sys.exit(0 if fail == 0 else 1)

        elif args.command == "export":
            success, fail = export_all(args.url, BACKUP_DIR)
            print(f"\nExport complete: {success} succeeded, {fail} failed")
            sys.exit(0 if fail == 0 else 1)

        elif args.command == "list":
            list_workflows(args.url)

    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to n8n at {args.url}")
        print("Make sure n8n is running and the URL is correct.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP error from n8n: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
