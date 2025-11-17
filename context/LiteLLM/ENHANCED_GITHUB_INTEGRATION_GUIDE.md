# 🚀 GitHub Copilot + LiteLLM: The Definitive Integration Guide

## 🎯 The Final Working Solution: A Modular & Automated Toolchain

After extensive reverse-engineering and testing, we have developed the **only reliable and maintainable method** to integrate GitHub Copilot with LiteLLM. The solution is a modular toolchain that automates authentication and configuration.

**The Problem**: The GitHub Copilot API is undocumented, requires a complex OAuth flow, and uses non-standard headers that are not supported by LiteLLM's dynamic features (`default_headers`, callbacks).

**The Solution**: We have built two standalone Python scripts to handle this complexity, generating a perfect, declarative LiteLLM configuration file.

### The Toolchain
1.  **`github_auth.py`**: A standalone script that performs the GitHub Device Code Flow to acquire a valid OAuth token, saving it to `github_token.json`. This completely decouples authentication from LiteLLM.
2.  **`update-github-models.py`**: A script that reads the token, queries the undocumented GitHub models API (`https://api.githubcopilot.com/models`), and generates a complete `auto-headers-config.yaml` with the correct declarative `extra_headers` for every model.

---

## ⚙️ The Automated Workflow

### Step 1: Authenticate (One-Time Setup)
Run the authentication script and follow the browser prompts. This creates your `github_token.json`.

```bash
# (Create and activate a venv if you haven't)
# python -m venv .venv && source .venv/bin/activate
# pip install requests pyyaml

python github_auth.py
```

### Step 2: Generate Your Configuration
Run the update script to create your `auto-headers-config.yaml`.

```bash
python update-github-models.py
```

### Step 3: Launch the LiteLLM Proxy
Start LiteLLM with the newly generated, perfect configuration.

```bash
litellm --config auto-headers-config.yaml --port 4000
```

---

## 🧪 Testing the Integration

With this setup, all API calls are simple and clean. The configuration handles all the complexity.

```bash
curl http://localhost:4000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-auto-headers-2025" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello from a working setup!"}]
  }'
```

---

## 🛠️ Key Technical Details & Findings

### The Correct OAuth `CLIENT_ID`
The device flow **must** use the `CLIENT_ID` for the official VS Code extension to be considered valid by GitHub. Any other ID will result in a `404 Not Found`.
- **Correct ID**: `Iv1.b507a08c87ecfe98`

### The Correct API Endpoint for Models
The endpoint for listing models is different from the main GitHub API.
- **Correct Endpoint**: `https://api.githubcopilot.com/models`

### The Only Reliable Header Method
Dynamic methods like callbacks or `default_headers` fail. The only working solution is to declaratively define the `extra_headers` block for each model in the `litellm_params` section of the config file.

```yaml
# Correct structure within auto-headers-config.yaml
- model_name: gpt-4o
  litellm_params:
    model: github_copilot/gpt-4o
    extra_headers:
      editor-version: "vscode/1.96.0"
      editor-plugin-version: "copilot/1.155.0"
      copilot-integration-id: "vscode-chat"
      user-agent: "GitHubCopilot/1.155.0"
```

## 🎉 Success!

You now have a **proven, reliable, and automated setup** for routing requests through your GitHub Copilot subscription.

### Key Takeaways:
- ✅ **Automation is key.** The `update-github-models.py` script ensures your configuration is always current.
- ✅ **Decoupling is robust.** Separating authentication (`github_auth.py`) from LiteLLM's state prevents hard-to-debug errors.
- ✅ **Declarative configuration is the only reliable method** for injecting the required headers.

**This guide reflects the final, successful architecture.**
