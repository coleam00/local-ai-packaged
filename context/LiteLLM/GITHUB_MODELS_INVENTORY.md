# GitHub Models Inventory & Configuration Status

## 📋 Dynamic Model Inventory

This project no longer uses a static, manually maintained list of GitHub models. Instead, we use a dynamic approach to ensure the model list is always up-to-date.

The `update-github-models.py` script connects directly to the official (undocumented) GitHub API endpoint (`https://api.githubcopilot.com/models`) and fetches the complete list of models available to your authenticated account.

### 🤖 Model Categories

The script automatically categorizes and configures two types of models:

1.  **GitHub Copilot Models (Dynamic List)**
    *   **Authentication**: OAuth2 (handled by `github_auth.py`).
    *   **Header Injection**: The script automatically adds the required `extra_headers` block to each of these models in the generated `auto-headers-config.yaml`.
    *   **Examples**: `gpt-4o`, `claude-3.5-sonnet`, `o3-mini`, etc. The exact list depends on what the API returns.

2.  **GitHub Marketplace Models (Static List)**
    *   **Authentication**: API Key (requires `GITHUB_API_KEY` environment variable).
    *   **Header Injection**: Not required.
    *   **Examples**: The script currently adds `llama-3-1-405b` and `phi-4` to the config, as these are not returned by the Copilot models API.

## 🔧 Configuration Status: ✅ Fully Automated

- **Model Definitions**: The `update-github-models.py` script generates the complete `model_list` for the `auto-headers-config.yaml` file.
- **Header Injection**: The script guarantees that all Copilot models receive the correct, declarative `extra_headers` block.
- **Test Suite**: To see which models are available to you, simply run the update script. The console output will show you how many models were found, and the generated YAML file will contain the complete list.

### 🚀 Usage Example
All models are called in the same, simple way. No client-side headers are needed.
```bash
curl -X POST http://localhost:4000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-auto-headers-2025" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 🎯 Next Steps
1.  Run `python github_auth.py` to authenticate (if you haven't already).
2.  Run `python update-github-models.py` to generate your config.
3.  Run `litellm --config auto-headers-config.yaml --port 4000`.
4.  Integrate with your applications by calling the model names found in the generated config.