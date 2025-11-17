#!/usr/bin/env python3
"""
Simple GitHub Headers Proxy for LiteLLM

This proxy automatically injects GitHub Copilot headers into requests
before forwarding them to LiteLLM, solving the header injection problem
without needing complex LiteLLM middleware.

Usage:
    python github_headers_proxy.py
    
Then use http://localhost:3999 as your API endpoint
(it forwards to LiteLLM at localhost:4000 with auto-injected headers)
"""

import json
import requests
from flask import Flask, request, jsonify, Response
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration
LITELLM_URL = "http://localhost:4000"
PROXY_PORT = 3999

# GitHub Copilot models that need header injection
GITHUB_COPILOT_MODELS = {
    'gpt-4o', 'gpt-4-turbo', 'gpt-4o-mini', 'gpt-4.1',
    'o1-preview', 'o1-mini', 'o3-mini',
    'claude-3-5-sonnet', 'claude-3-5-sonnet-latest', 'claude-3-5-haiku',
    'gemini-2-0-flash-exp', 'gemini-1-5-pro', 'gemini-1-5-flash'
}

# Required GitHub headers
GITHUB_HEADERS = {
    "editor-version": "vscode/1.96.0",
    "editor-plugin-version": "copilot/1.155.0",
    "copilot-integration-id": "vscode-chat",
    "user-agent": "GitHubCopilot/1.155.0"
}

def is_github_copilot_model(model_name):
    """Check if a model needs GitHub headers"""
    return model_name in GITHUB_COPILOT_MODELS

def inject_github_headers(request_data):
    """Inject GitHub headers if needed"""
    model = request_data.get('model', '')
    
    if is_github_copilot_model(model):
        # Initialize extra_headers if not present
        if 'extra_headers' not in request_data:
            request_data['extra_headers'] = {}
        
        # Inject required headers
        request_data['extra_headers'].update(GITHUB_HEADERS)
        
        app.logger.info(f"✅ Auto-injected GitHub headers for {model}")
        return True
    
    return False

@app.route('/chat/completions', methods=['POST'])
def chat_completions():
    """Proxy chat completions with automatic header injection"""
    try:
        # Get original request data
        request_data = request.get_json()
        
        if not request_data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Inject headers if needed
        headers_injected = inject_github_headers(request_data)
        
        # Forward to LiteLLM
        headers = {
            'Content-Type': 'application/json',
            'Authorization': request.headers.get('Authorization', '')
        }
        
        response = requests.post(
            f"{LITELLM_URL}/chat/completions",
            json=request_data,
            headers=headers,
            timeout=120
        )
        
        # Log success/failure
        if response.status_code == 200 and headers_injected:
            app.logger.info(f"✅ GitHub Copilot call successful: {request_data.get('model', 'unknown')}")
        elif response.status_code != 200 and headers_injected:
            app.logger.error(f"❌ GitHub Copilot call failed: {request_data.get('model', 'unknown')}")
        
        # Return response
        return Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )
        
    except Exception as e:
        app.logger.error(f"❌ Proxy error: {str(e)}")
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "proxy_port": PROXY_PORT,
        "litellm_url": LITELLM_URL,
        "github_models": list(GITHUB_COPILOT_MODELS)
    })

@app.route('/v1/models', methods=['GET'])
def models():
    """Forward models endpoint"""
    try:
        headers = {'Authorization': request.headers.get('Authorization', '')}
        response = requests.get(f"{LITELLM_URL}/v1/models", headers=headers)
        
        return Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        return jsonify({"error": f"Models endpoint error: {str(e)}"}), 500

if __name__ == '__main__':
    print("🚀 Starting GitHub Headers Auto-Injection Proxy")
    print("=" * 50)
    print(f"📍 Proxy running on: http://localhost:{PROXY_PORT}")
    print(f"🔗 Forwarding to LiteLLM: {LITELLM_URL}")
    print(f"🎯 Auto-injecting headers for {len(GITHUB_COPILOT_MODELS)} GitHub models")
    print("=" * 50)
    print()
    print("🧪 Test with:")
    print(f'curl -X POST http://localhost:{PROXY_PORT}/chat/completions \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -H "Authorization: Bearer your-key" \\')
    print('  -d \'{"model": "gpt-4o", "messages": [{"role": "user", "content": "test"}]}\'')
    print()
    
    app.run(host='0.0.0.0', port=PROXY_PORT, debug=False)