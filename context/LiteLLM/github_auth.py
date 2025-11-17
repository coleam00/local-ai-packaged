#!/usr/bin/env python3
"""
GitHub Copilot Standalone Authenticator.

This script performs the GitHub Device Code Flow to obtain an OAuth token
for the GitHub Copilot API, completely independent of LiteLLM.

It replicates the authentication method used by the official VS Code extension
and other reverse-engineered tools.

Usage:
    1. Run the script: python3 github_auth.py
    2. Follow the on-screen instructions to authorize the application in your browser.
    3. Upon success, it will create a `github_token.json` file in the current
       directory containing your access token.
"""

import time
import json
import requests
from pathlib import Path

# This is the public, hardcoded Client ID for the "GitHub Copilot" OAuth app
# used by the official VS Code extension.
CLIENT_ID = "Iv1.b507a08c87ecfe98"
DEVICE_CODE_URL = "https://github.com/login/device/code"
OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
TOKEN_FILE_PATH = Path("github_token.json")

def get_device_code():
    """
    Step 1: Request a device and user code from GitHub.
    """
    print("1. Requesting device code from GitHub...")
    response = requests.post(
        DEVICE_CODE_URL,
        headers={"Accept": "application/json"},
        data={"client_id": CLIENT_ID, "scope": "read:user"},
    )
    response.raise_for_status()
    data = response.json()
    print("   ✅ Received device code.")
    return data

def poll_for_token(device_code_data: dict):
    """
    Step 2: Poll GitHub until the user authorizes the app in their browser.
    """
    print("\n2. Waiting for you to authorize in the browser...")
    
    params = {
        "client_id": CLIENT_ID,
        "device_code": device_code_data["device_code"],
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    
    interval = device_code_data.get("interval", 5);
    
    while True:
        time.sleep(interval)
        response = requests.post(
            OAUTH_TOKEN_URL,
            headers={"Accept": "application/json"},
            data=params,
        )
        response.raise_for_status()
        data = response.json()
        
        error = data.get("error")
        if error == "authorization_pending":
            print("   ... still waiting for authorization")
            continue
        elif error == "slow_down":
            interval += 5
            print(f"   ... polling too fast, slowing down to {interval}s")
            continue
        elif error:
            raise Exception(f"GitHub API error: {data.get('error_description', 'Unknown error')}")
        
        access_token = data.get("access_token")
        if access_token:
            print("   ✅ Authorization successful! Received access token.")
            return access_token

def main():
    """Main function to run the authentication flow."""
    print("🚀 Starting GitHub Copilot Authentication 🚀")
    try:
        device_code_data = get_device_code()
        
        print("\n" + "="*60)
        print("ACTION REQUIRED:")
        print(f"Please go to: {device_code_data['verification_uri']}")
        print(f"And enter this code: {device_code_data['user_code']}")
        print("="*60)
        
        access_token = poll_for_token(device_code_data)
        
        print(f"\n3. Saving token to '{TOKEN_FILE_PATH}'...")
        with open(TOKEN_FILE_PATH, "w") as f:
            json.dump({"access_token": access_token}, f, indent=2)
        print("   ✅ Token saved successfully.")
        
        print("\n🎉 --- Authentication Complete! --- 🎉")
        print("You can now run `update-github-models.py` to generate your config.")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Network Error: Failed to connect to GitHub API. {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
