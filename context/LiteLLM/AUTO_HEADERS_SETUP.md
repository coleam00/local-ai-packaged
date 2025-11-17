# 🚀 GitHub Copilot Integration: Automated Setup Guide

## 🎯 The Goal: Simple, Reliable Access to GitHub Models

This guide provides the definitive, automated workflow for integrating GitHub Copilot with LiteLLM. The process uses a standalone authentication script and a dynamic config generator to create a perfect, up-to-date configuration file every time.

**This solution makes manual configuration and debugging obsolete.**

## 🚀 The Automated Workflow

### Step 1: Authenticate with GitHub (One-Time Setup)
First, we need to get an authentication token from GitHub. Our standalone script handles the complex Device Code Flow for you.

```bash
# (If you haven't created the virtual environment yet)
# python -m venv .venv
# source .venv/bin/activate
# pip install requests pyyaml

# Run the authentication script
python github_auth.py
```
Follow the on-screen instructions to authorize the app in your browser. This will create a `github_token.json` file in your directory. You only need to do this once.

### Step 2: Generate the LiteLLM Configuration
Next, run the update script. It will read your token, fetch the latest list of models available to your account, and build the configuration file.

```bash
python update-github-models.py
```
This will create a new, perfectly formatted `auto-headers-config.yaml` file.

### Step 3: Launch LiteLLM
You are now ready to start the proxy with your fresh, complete configuration.

```bash
litellm --config auto-headers-config.yaml --port 4000
```

### Step 4: Test Any Model
You can now make simple, clean API calls to any model listed in the config, like `gpt-4o` or `claude-3.5-sonnet`.

```bash
curl -X POST http://localhost:4000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-auto-headers-2025" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "This is a test."}]
  }'
```

## 🔧 The Toolchain

This automated solution is powered by two key files:
- `github_auth.py`: A standalone script to handle the complex GitHub OAuth2 device flow.
- `update-github-models.py`: A script that uses the token from the auth script to fetch the latest model list and generate the final `auto-headers-config.yaml`.

## 🏁 Success Criteria

✅ The `github_auth.py` script completes successfully, creating `github_token.json`.  
✅ The `update-github-models.py` script runs without errors, creating `auto-headers-config.yaml`.  
✅ The LiteLLM server starts correctly with the new config.  
✅ API calls to available models (like `gpt-4o`) receive a `200 OK` response.

**This modular and automated workflow is the definitive solution for integrating GitHub Copilot with LiteLLM.**