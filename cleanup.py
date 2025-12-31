#!/usr/bin/env python3
"""
cleanup.py

This script performs a complete cleanup of the local-ai-packaged project,
removing all Docker containers, volumes, networks, and project directories
to enable a fresh start.

CAUTION: This script is DESTRUCTIVE. All data will be permanently deleted.
"""

import os
import sys
import shutil
import argparse
import docker
from typing import List, Tuple

def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")

def print_item(text: str, prefix: str = "  -") -> None:
    """Print an item in a list."""
    print(f"{prefix} {text}")

def get_directories_to_remove() -> List[str]:
    """Get list of project directories to remove."""
    dirs = [
        "supabase",
        ".env_backups",
        ".venv",
        "neo4j/logs",
        "neo4j/config",
        "neo4j/data",
        "neo4j/plugins"
    ]

    # Only return directories that actually exist
    return [d for d in dirs if os.path.exists(d)]

def get_files_to_remove(preserve_env: bool = False) -> List[str]:
    """Get list of project files to remove."""
    files = [
        "searxng/settings.yml",
        "nul"  # temp file that exists in the project
    ]

    if not preserve_env:
        files.append(".env")

    # Only return files that actually exist
    return [f for f in files if os.path.exists(f)]

def get_docker_resources() -> Tuple[List, List, List, List]:
    """
    Get all Docker resources belonging to this project.
    Returns: (containers, named_volumes, networks, anonymous_volumes)
    """
    try:
        client = docker.from_env()
    except docker.errors.DockerException as e:
        print(f"Error connecting to Docker: {e}")
        print("Is Docker running?")
        sys.exit(1)

    # Find containers with project label
    project_label = "com.docker.compose.project=localai"
    containers = client.containers.list(
        all=True,
        filters={"label": project_label}
    )

    # Find volumes with project prefix
    all_volumes = client.volumes.list()
    volumes = [v for v in all_volumes if v.name.startswith("localai_")]

    # Find networks with project label or name
    all_networks = client.networks.list()
    networks = [
        n for n in all_networks
        if n.name.startswith("localai") or
           project_label in [f"{k}={v}" for k, v in n.attrs.get("Labels", {}).items()]
    ]

    # Find anonymous volumes attached to project containers
    anonymous_volumes = []
    for container in containers:
        try:
            # Get container details to inspect mounts
            container.reload()
            mounts = container.attrs.get('Mounts', [])

            for mount in mounts:
                if mount.get('Type') == 'volume':
                    vol_name = mount.get('Name')
                    # Anonymous volumes are 64-char hex strings
                    if vol_name and len(vol_name) == 64:
                        if all(c in '0123456789abcdef' for c in vol_name):
                            try:
                                vol = client.volumes.get(vol_name)
                                anonymous_volumes.append(vol)
                            except:
                                pass
        except Exception:
            pass

    # Also find dangling anonymous volumes (not currently attached to containers)
    # These can be left behind when containers are removed
    try:
        all_volumes = client.volumes.list()
        for vol in all_volumes:
            # Check if it's an anonymous volume (64-char hex name)
            if (len(vol.name) == 64 and
                all(c in '0123456789abcdef' for c in vol.name) and
                vol.attrs.get('Labels', {}).get('com.docker.volume.anonymous') == ''):
                anonymous_volumes.append(vol)
    except Exception:
        pass

    # Deduplicate anonymous volumes
    anonymous_volumes = list({v.name: v for v in anonymous_volumes}.values())

    return containers, volumes, networks, anonymous_volumes

def preview_cleanup(preserve_env: bool = False) -> bool:
    """
    Preview what will be deleted. Returns True if anything found to delete.
    """
    print_header("CLEANUP PREVIEW")

    has_items = False

    # Docker resources
    containers, volumes, networks, anonymous_volumes = get_docker_resources()

    if containers:
        has_items = True
        print("\nDocker Containers (will be stopped and removed):")
        for c in containers:
            print_item(f"{c.name} ({c.short_id})")

    if volumes:
        has_items = True
        print("\nDocker Volumes (will be removed):")
        for v in volumes:
            print_item(v.name)

    if networks:
        has_items = True
        print("\nDocker Networks (will be removed):")
        for n in networks:
            print_item(n.name)

    if anonymous_volumes:
        has_items = True
        print("\nAnonymous Docker Volumes (created when bind mounts failed):")
        for v in anonymous_volumes:
            print_item(f"{v.name[:12]}... (full: {v.name})")
        print("  These will be removed to prevent database persistence issues.")

    # Directories
    dirs = get_directories_to_remove()
    if dirs:
        has_items = True
        print("\nDirectories (will be deleted):")
        for d in dirs:
            print_item(d)

    # Files
    files = get_files_to_remove(preserve_env)
    if files:
        has_items = True
        print("\nFiles (will be deleted):")
        for f in files:
            print_item(f)

    if preserve_env:
        print("\n.env file will be PRESERVED")

    if not has_items:
        print("No project resources found to clean up.")

    return has_items

def cleanup_docker_resources(dry_run: bool = False) -> None:
    """Stop and remove all Docker resources for this project."""
    print_header("Cleaning Docker Resources")

    containers, volumes, networks, anonymous_volumes = get_docker_resources()

    # Stop and remove containers
    if containers:
        print(f"\nStopping and removing {len(containers)} container(s)...")
        for container in containers:
            try:
                if not dry_run:
                    print_item(f"Stopping {container.name}...")
                    container.stop(timeout=10)
                    print_item(f"Removing {container.name}...")
                    container.remove(force=True)
                else:
                    print_item(f"Would stop and remove: {container.name}")
            except Exception as e:
                print(f"    Error with container {container.name}: {e}")

    # Remove volumes
    if volumes:
        print(f"\nRemoving {len(volumes)} volume(s)...")
        for volume in volumes:
            try:
                if not dry_run:
                    print_item(f"Removing {volume.name}...")
                    volume.remove(force=True)
                else:
                    print_item(f"Would remove: {volume.name}")
            except Exception as e:
                print(f"    Error with volume {volume.name}: {e}")

    # Remove networks
    if networks:
        print(f"\nRemoving {len(networks)} network(s)...")
        for network in networks:
            try:
                # Skip default networks
                if network.name in ["bridge", "host", "none"]:
                    print_item(f"Skipping default network: {network.name}")
                    continue

                if not dry_run:
                    print_item(f"Removing {network.name}...")
                    network.remove()
                else:
                    print_item(f"Would remove: {network.name}")
            except Exception as e:
                print(f"    Error with network {network.name}: {e}")

    # Remove anonymous volumes
    if anonymous_volumes:
        print(f"\nRemoving {len(anonymous_volumes)} anonymous volume(s)...")
        for volume in anonymous_volumes:
            try:
                if not dry_run:
                    print_item(f"Removing {volume.name[:12]}...")
                    volume.remove(force=True)
                else:
                    print_item(f"Would remove: {volume.name[:12]}...")
            except Exception as e:
                print(f"    Error with volume {volume.name[:12]}: {e}")

def handle_remove_readonly(func, path, exc_info):
    """
    Error handler for Windows readonly files.
    From Python docs: https://docs.python.org/3/library/shutil.html#rmtree-example
    """
    import stat
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise

def cleanup_filesystem(preserve_env: bool = False, dry_run: bool = False) -> None:
    """Remove all project directories and files."""
    print_header("Cleaning Filesystem")

    # Remove directories
    dirs = get_directories_to_remove()
    if dirs:
        print(f"\nRemoving {len(dirs)} director(y/ies)...")
        for dir_path in dirs:
            try:
                if not dry_run:
                    print_item(f"Removing {dir_path}/...")
                    shutil.rmtree(dir_path, onerror=handle_remove_readonly)
                else:
                    print_item(f"Would remove: {dir_path}/")
            except Exception as e:
                print(f"    Error removing {dir_path}: {e}")

    # Remove files
    files = get_files_to_remove(preserve_env)
    if files:
        print(f"\nRemoving {len(files)} file(s)...")
        for file_path in files:
            try:
                if not dry_run:
                    print_item(f"Removing {file_path}")
                    os.remove(file_path)
                else:
                    print_item(f"Would remove: {file_path}")
            except Exception as e:
                print(f"    Error removing {file_path}: {e}")

    # Also check for empty PostgreSQL data directory
    # This can cause initialization issues if left in place
    supabase_db_data = os.path.join("supabase", "docker", "volumes", "db", "data")
    if os.path.exists(supabase_db_data):
        try:
            entries = os.listdir(supabase_db_data)
            if not entries:
                if not dry_run:
                    print_item(f"Removing empty PostgreSQL directory: {supabase_db_data}")
                    os.rmdir(supabase_db_data)
                else:
                    print_item(f"Would remove empty PostgreSQL directory: {supabase_db_data}")
        except Exception:
            pass  # Best effort

def confirm_cleanup() -> bool:
    """Ask user for explicit confirmation."""
    print("\n" + "!" * 60)
    print("  WARNING: This operation is IRREVERSIBLE")
    print("  All project data will be PERMANENTLY DELETED")
    print("!" * 60)

    response = input("\nType 'DELETE' (all caps) to confirm: ")
    return response == "DELETE"

def main():
    parser = argparse.ArgumentParser(
        description='Clean up all local-ai-packaged project resources for a fresh start.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup.py --dry-run              Preview what will be deleted
  python cleanup.py                        Clean everything, ask about .env
  python cleanup.py --preserve-env         Clean everything except .env
  python cleanup.py --force                Clean everything including .env (no prompts)
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what will be deleted without actually deleting'
    )

    parser.add_argument(
        '--preserve-env',
        action='store_true',
        help='Keep the .env file (preserve your configuration)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompts (DANGEROUS - deletes everything including .env)'
    )

    args = parser.parse_args()

    # Override preserve-env if force is used
    preserve_env = args.preserve_env or (not args.force and not args.dry_run)

    # If not in dry-run and not force, ask about .env
    if not args.dry_run and not args.force and not args.preserve_env:
        response = input("\nDo you want to preserve the .env file? [Y/n]: ").strip().lower()
        # Preserve by default (Y), only delete if explicitly 'n' or 'no'
        preserve_env = response not in ['n', 'no']

    # Preview
    has_items = preview_cleanup(preserve_env)

    if not has_items:
        print("\n✓ Project already clean!")
        return 0

    # Dry run exits here
    if args.dry_run:
        print("\n(Dry run - nothing was deleted)")
        return 0

    # Confirm
    if not args.force:
        if not confirm_cleanup():
            print("\nCleanup cancelled.")
            return 0

    # Execute cleanup
    print_header("EXECUTING CLEANUP")

    cleanup_docker_resources(dry_run=False)
    cleanup_filesystem(preserve_env=preserve_env, dry_run=False)

    print_header("CLEANUP COMPLETE")
    print("Project has been reset to clean state.")
    print("You can now run: python start_services.py --profile <your-profile>")

    return 0

if __name__ == "__main__":
    sys.exit(main())
