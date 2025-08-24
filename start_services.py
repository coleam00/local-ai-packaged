#!/usr/bin/env python3
"""
start_services.py  —  run the Local‑AI stack in *your* environment
- No Supabase, no Caddy. Traefik is external.
- Uses your existing docker-compose.yml (+ optional overrides).
- Generates SearXNG secret on first run.
- Works on Windows/macOS/Linux (Git Bash / PowerShell okay).

Usage examples:
  python start_services.py                 # cpu profile, private overrides if present
  python start_services.py --profile gpu-nvidia
  python start_services.py --env public --project localai
  python start_services.py --down          # stop stack

Files auto-detected if present:
  - docker-compose.override.yml
  - docker-compose.override.private.yml
  - docker-compose.override.public.yml
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
from pathlib import Path

PROJECT_DEFAULT = "localai"
COMPOSE_BASE = "docker-compose.yml"
OVERRIDE_GENERIC = "docker-compose.override.yml"
OVERRIDE_PRIVATE = "docker-compose.override.private.yml"
OVERRIDE_PUBLIC = "docker-compose.override.public.yml"

SEARXNG_DIR = Path("searxng")
SEARXNG_SETTINGS = SEARXNG_DIR / "settings.yml"
SEARXNG_SETTINGS_BASE = SEARXNG_DIR / "settings-base.yml"

def run(cmd, cwd=None, check=True, env=None):
    print("➜", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=check, env=env)

def docker_compose_cmd(project: str, profile: str, env_mode: str):
    """
    Build a docker compose command list with discovered override files.
    """
    files = [COMPOSE_BASE]
    if Path(OVERRIDE_GENERIC).exists():
        files.append(OVERRIDE_GENERIC)
    if env_mode == "private" and Path(OVERRIDE_PRIVATE).exists():
        files.append(OVERRIDE_PRIVATE)
    if env_mode == "public" and Path(OVERRIDE_PUBLIC).exists():
        files.append(OVERRIDE_PUBLIC)

    cmd = ["docker", "compose", "-p", project]
    if profile and profile != "none":
        cmd += ["--profile", profile]
    for f in files:
        cmd += ["-f", f]
    return cmd

def ensure_searxng_secret():
    """
    Create searxng/settings.yml from settings-base.yml and replace 'ultrasecretkey'
    with a random 32-byte hex key. Cross-platform.
    """
    SEARXNG_DIR.mkdir(parents=True, exist_ok=True)
    if not SEARXNG_SETTINGS.exists():
        if SEARXNG_SETTINGS_BASE.exists():
            print("• Creating searxng/settings.yml from settings-base.yml")
            shutil.copyfile(SEARXNG_SETTINGS_BASE, SEARXNG_SETTINGS)
        else:
            print("• Creating minimal searxng/settings.yml")
            SEARXNG_SETTINGS.write_text("server:\n  secret_key: ultrasecretkey\n")

    # Generate 32-byte hex key
    system = platform.system()
    try:
        if system == "Windows":
            ps = [
                "powershell", "-NoProfile", "-Command",
                "$rb = New-Object byte[] 32; "
                "(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($rb); "
                "$k = -join ($rb | ForEach-Object { '{0:x2}' -f $_ }); "
                "(Get-Content 'searxng/settings.yml') -replace 'ultrasecretkey', $k | "
                "Set-Content 'searxng/settings.yml'"
            ]
            run(ps)
        else:
            # Linux/macOS
            key = subprocess.check_output(["openssl", "rand", "-hex", "32"]).decode("utf-8").strip()
            txt = SEARXNG_SETTINGS.read_text()
            if "ultrasecretkey" in txt:
                SEARXNG_SETTINGS.write_text(txt.replace("ultrasecretkey", key))
            else:
                # if not present, append it
                with open(SEARXNG_SETTINGS, "a") as f:
                    f.write(f"\nserver:\n  secret_key: {key}\n")
        print("• SearXNG secret_key set.")
    except Exception as e:
        print(f"⚠️ Could not set SearXNG secret automatically: {e}")

def first_run_searxng_soften_caps():
    """
    Some environments need to relax searxng caps on first boot.
    If docker-compose.yml contains 'cap_drop: - ALL', temporarily comment it.
    This is idempotent and reversible (only touches a line containing that exact token).
    """
    path = Path(COMPOSE_BASE)
    if not path.exists():
        return
    content = path.read_text()
    marker = "cap_drop: - ALL"
    commented = "# cap_drop: - ALL  # first-run"
    if marker in content:
        print("• Temporarily commenting 'cap_drop: - ALL' for SearXNG first run")
        path.write_text(content.replace(marker, commented))

def restore_searxng_caps_if_ready(project: str):
    """
    If searxng container is running and initialized, restore cap_drop.
    """
    try:
        names = subprocess.check_output(
            ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"]
        ).decode().strip().splitlines()
        if not names or not any(n for n in names):
            return
        # quick check inside container for uwsgi.ini presence
        cname = names[0]
        out = subprocess.run(
            ["docker", "exec", cname, "sh", "-c", "[ -f /etc/searxng/uwsgi.ini ] && echo ok || echo no"],
            capture_output=True, text=True
        )
        if out.stdout.strip() != "ok":
            return
        path = Path(COMPOSE_BASE)
        if not path.exists():
            return
        content = path.read_text()
        commented = "# cap_drop: - ALL  # first-run"
        if commented in content:
            print("• Restoring 'cap_drop: - ALL' in docker-compose.yml")
            path.write_text(content.replace(commented, "cap_drop: - ALL"))
    except Exception:
        pass

def up(project: str, profile: str, env_mode: str):
    ensure_searxng_secret()
    first_run_searxng_soften_caps()

    base_cmd = docker_compose_cmd(project, profile, env_mode)
    env = os.environ.copy()
    if profile and profile != "none":
        # also export for images that read COMPOSE_PROFILES
        env["COMPOSE_PROFILES"] = profile

    # up
    run(base_cmd + ["up", "-d"], env=env)

    # give searxng a moment, then restore caps if we changed them
    time.sleep(3)
    restore_searxng_caps_if_ready(project)

def down(project: str, profile: str, env_mode: str):
    base_cmd = docker_compose_cmd(project, profile, env_mode)
    run(base_cmd + ["down", "-v"])

def main():
    ap = argparse.ArgumentParser(description="Start/stop Local‑AI stack (no Supabase, Traefik external).")
    ap.add_argument("--project", default=PROJECT_DEFAULT, help=f"Docker compose project name (default: {PROJECT_DEFAULT})")
    ap.add_argument("--profile", choices=["cpu", "gpu-nvidia", "gpu-amd", "none"], default="cpu",
                    help="Compose profile (default: cpu)")
    ap.add_argument("--env", choices=["private", "public"], default="private",
                    help="Environment to use if override files exist (default: private)")
    ap.add_argument("--down", action="store_true", help="Stop and remove the stack")
    args = ap.parse_args()

    # sanity checks
    if not Path(COMPOSE_BASE).exists():
        print(f"❌ {COMPOSE_BASE} not found in {Path.cwd()}")
        raise SystemExit(1)

    if args.down:
        down(args.project, args.profile, args.env)
    else:
        up(args.project, args.profile, args.env)

if __name__ == "__main__":
    main()
