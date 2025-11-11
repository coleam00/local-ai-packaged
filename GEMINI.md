## Project Overview

This project provides a self-hosted AI development environment using Docker. It includes a variety of services to facilitate the creation and management of local AI agents and workflows. This is a community-driven project, curated by https://github.com/n8n-io and https://github.com/coleam00, and it combines the self-hosted n8n platform with a curated list of compatible AI products and components to quickly get started with building self-hosted AI workflows.

## What’s included

*   [**Self-hosted n8n**](https://n8n.io/): Low-code platform with over 400 integrations and advanced AI components.
*   [**Supabase**](https://supabase.com/): Open source database as a service - most widely used database for AI agents.
*   [**Ollama**](https://ollama.com/): Cross-platform LLM platform to install and run the latest local LLMs.
*   [**Open WebUI**](https://openwebui.com/): ChatGPT-like interface to privately interact with your local models and N8N agents.
*   [**Flowise**](https://flowiseai.com/): No/low code AI agent builder that pairs very well with n8n.
*   [**Qdrant**](https://qdrant.tech/): Open source, high performance vector store with an comprehensive API.
*   [**Neo4j**](https://neo4j.com/): Knowledge graph engine that powers tools like GraphRAG, LightRAG, and Graphiti.
*   [**SearXNG**](https://searxng.org/): Open source, free internet metasearch engine which aggregates results from up to 229 search services.
*   [**Caddy**](https://caddyserver.com/): Managed HTTPS/TLS for custom domains.
*   [**Langfuse**](https://langfuse.com/): Open source LLM engineering platform for agent observability.

## Prerequisites

*   [Python](https://www.python.org/downloads/)
*   [Git/GitHub Desktop](https://desktop.github.com/)
*   [Docker/Docker Desktop](https://www.docker.com/products/docker-desktop/)

## Installation

1.  Clone the repository:
    ```bash
    git clone -b stable https://github.com/coleam00/local-ai-packaged.git
    cd local-ai-packaged
    ```
2.  Create a `.env` file from `.env.example` and set the required environment variables.

## Running the Services

The `start_services.py` script is used to start the services.

*   **NVIDIA GPU:**
    ```bash
    python start_services.py --profile gpu-nvidia
    ```
*   **AMD GPU (Linux):**
    ```bash
    python start_services.py --profile gpu-amd
    ```
*   **CPU only:**
    ```bash
    python start_services.py --profile cpu
    ```
*   **Mac / Apple Silicon (Ollama running on host):**
    ```bash
    python start_services.py --profile none
    ```

The script also accepts an `--environment` flag (`private` or `public`).

## Deploying to the Cloud

1.  Open ports 80 and 443.
2.  Run `start_services.py` with `--environment public`.
3.  Set up A records for your DNS provider.

## Quick Start and Usage

1.  Set up n8n at `http://localhost:5678/`.
2.  Open the included workflow at `http://localhost:5678/workflow/vTN9y2dLXqTiDfPT`.
3.  Create credentials for the services.
4.  Set up Open WebUI at `http://localhost:3000/`.
5.  Add the `n8n_pipe.py` function to Open WebUI.

## Upgrading

```bash
# Stop all services
docker compose -p localai -f docker-compose.yml --profile <your-profile> down

# Pull latest versions of all containers
docker compose -p localai -f docker-compose.yml --profile <your-profile> pull

# Start services again with your desired profile
python start_services.py --profile <your-profile>
```

## Troubleshooting

Refer to the `README.md` for solutions to common issues.

## Recommended Reading

*   [AI agents for developers: from theory to practice with n8n](https://blog.n8n.io/ai-agents/)
*   [Tutorial: Build an AI workflow in n8n](https://docs.n8n.io/advanced-ai/intro-tutorial/)
*   [Langchain Concepts in n8n](https://docs.n8n.io/advanced-ai/langchain/langchain-n8n/)

## Video Walkthrough

*   [Cole's Guide to the Local AI Starter Kit](https://youtu.be/pOsO40HSbOo)

## More AI Templates

*   [Official n8n AI template gallery](https://n8n.io/workflows/?categories=AI)

## Tips & Tricks

The shared folder is mounted at `/data/shared` in the n8n container.

## License

This project is licensed under the Apache License 2.0.

## Gemini Added Memories
- CyberSec_Cams