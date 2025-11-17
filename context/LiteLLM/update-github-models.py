#!/usr/bin/env python3
"""
Dynamically Generates the LiteLLM Configuration for GitHub Models.

This script fetches the latest list of available GitHub Copilot and Marketplace
models from the official GitHub API and generates a perfectly formatted LiteLLM
configuration file (`auto-headers-config.yaml`).

This automates the process of keeping the model list up-to-date, ensuring
that as GitHub adds or removes models, your configuration can be updated
with a single command.

Usage:
    1. Ensure you have authenticated with LiteLLM at least once to generate
       the necessary OAuth token.
    2. Run the script: python3 update-github-models.py
    3. A new `auto-headers-config.yaml` file will be created with the latest models.
    4. Start LiteLLM with the new config: litellm --config auto-headers-config.yaml
"""

import os
import json
import requests
import yaml
from pathlib import Path

# --- Configuration ---
# The hidden, undocumented API endpoint that the official VS Code extension uses
# to list available models. This was discovered through community reverse-engineering
# as no official public API is available for this purpose (as of late 2025).
MODELS_API_URL = "https://api.githubcopilot.com/models"

# The local file where `github_auth.py` saves the token.
TOKEN_FILE_PATH = Path("github_token.json")

# The name of the output file that will be generated.
OUTPUT_CONFIG_FILE = "auto-headers-config.yaml"

# The required headers to simulate a VSCode client.
# These are necessary for both authentication and for the `extra_headers` block.
REQUIRED_HEADERS = {
    "editor-version": "vscode/1.96.0",
    "editor-plugin-version": "copilot/1.155.0",
    "copilot-integration-id": "vscode-chat",
    "user-agent": "GitHubCopilot/1.155.0",
}

# --- Main Script Logic ---

def get_oauth_token() -> str:
    """
    Reads the GitHub OAuth token from the local `github_token.json` file.
    
    Returns:
        The OAuth token as a string.
        
    Raises:
        FileNotFoundError: If the token file does not exist.
    """
    print(f"🔍 Reading OAuth token from: {TOKEN_FILE_PATH}")
    if not TOKEN_FILE_PATH.is_file():
        raise FileNotFoundError(
            f"'{TOKEN_FILE_PATH}' not found.\n"
            "Please run `python3 github_auth.py` first to generate it."
        )
    with open(TOKEN_FILE_PATH, "r") as f:
        token_data = json.load(f)
        return token_data["access_token"]

def fetch_available_models(token: str) -> list:
    """
    Fetches the list of available models from the GitHub API.
    
    Args:
        token: The OAuth token for authentication.
        
    Returns:
        A list of model dictionaries from the API response.
    """
    print(f"📡 Fetching latest model list from {MODELS_API_URL}...")
    headers = {
        "Authorization": f"Bearer {token}",
        **REQUIRED_HEADERS
    }
    response = requests.get(MODELS_API_URL, headers=headers)
    response.raise_for_status()  # Raise an exception for bad status codes
    
    models = response.json().get("data", [])
    print(f"✅ Found {len(models)} available models.")
    return models

def generate_new_model_list(models: list) -> list:
    """
    Generates just the 'model_list' part of the configuration.
    """
    print("⚙️ Generating new model list...")
    model_list = []
    for model in sorted(models, key=lambda m: m["id"]):
        model_entry = {
            "model_name": model["id"],
            "litellm_params": {
                "model": f"github_copilot/{model['id']}",
                "extra_headers": REQUIRED_HEADERS,
            },
        }
        model_list.append(model_entry)

    # Manually add the Marketplace models as they are not in the Copilot API
    model_list.extend([
        {
            "model_name": "llama-3-1-405b",
            "litellm_params": {
                "model": "github/Llama-3.1-405B-Instruct",
                "api_key": "os.environ/GITHUB_API_KEY",
            },
        },
        {
            "model_name": "phi-4",
            "litellm_params": {
                "model": "github/Phi-4",
                "api_key": "os.environ/GITHUB_API_KEY",
            },
        },
    ])
    return model_list

def main():
    """Main function to run the script."""
    print("🚀 Starting GitHub Model Config Updater...")
    try:
        # Step 1: Fetch the latest models from the API
        token = get_oauth_token()
        models = fetch_available_models(token)
        
        # Step 2: Generate just the new model list
        new_model_list = generate_new_model_list(models)
        
        # Step 3: Read the existing config file to preserve its structure and comments
        print(f"📖 Reading existing configuration from {OUTPUT_CONFIG_FILE}...")
        if not Path(OUTPUT_CONFIG_FILE).is_file():
            raise FileNotFoundError(f"The master config file '{OUTPUT_CONFIG_FILE}' was not found. Cannot update.")
            
        with open(OUTPUT_CONFIG_FILE, "r") as f:
            # We use a special loader to preserve comments if possible, but ruamel.yaml is not a default dependency.
            # For now, standard yaml load/dump will preserve structure.
            existing_config = yaml.safe_load(f)
            
        # Step 4: Surgically replace the 'model_list'
        print("🔄 Replacing the model_list in the existing configuration...")
        existing_config["model_list"] = new_model_list
        
        # Step 5: Write the updated configuration back to the file
        print(f"💾 Saving updated configuration back to {OUTPUT_CONFIG_FILE}...")
        with open(OUTPUT_CONFIG_FILE, "w") as f:
            yaml.dump(existing_config, f, sort_keys=False, indent=2)
            
        print("\n🎉 --- Success! --- 🎉")
        print(f"'{OUTPUT_CONFIG_FILE}' has been updated with the latest models.")
        print("All other settings and comments have been preserved.")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error fetching models from GitHub API: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
