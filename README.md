# DocAns: Fully Local & Private AI Document Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**DocAns** is a fully local, private AI document assistant and low-code development environment. It quickly bootstraps a comprehensive local AI stack, including Ollama for your local LLMs, Open WebUI for an interface to chat with your N8N agents, and Supabase for your database, vector store, and authentication.

This project merges the core local AI infrastructure from the [local-ai-packaged](https://github.com/coleam00/local-ai-packaged) repository with the frontend and workflows of [InsightsLM](https://github.com/theaiautomators/insights-lm-public), modified to run completely offline. Ensure total privacy and control over your data!

---

## 🚀 Key Features

* **Run Completely Offline:** All services run locally in Docker containers. Your data never leaves your machine.
* **Self-hosted n8n:** Low-code platform with over 400 integrations and advanced AI components.
* **Chat with Your Documents:** Upload PDFs, text files, and audio files to get instant, context-aware answers from a local LLM via Open WebUI or the custom InsightsLM frontend.
* **Local Audio Transcription:** Transcribe audio files using a local Whisper container.
* **Local Podcast Generation:** Create audio summaries from your source materials using local Coqui text-to-speech models.
* **Comprehensive Stack:** Includes Supabase, Flowise, Qdrant, Neo4j, SearXNG, Caddy, Langfuse, and more.

---

## 🛠️ Architecture & Built With

This project runs a suite of services locally using Docker. The core components include:

* **Frontend Apps:** Open WebUI (General AI Chat), Flowise (No-code Agents), InsightsLM (Document Assistant React/Vite App)
* **Backend & Automation:** N8N
* **Database & Storage:** Supabase (running locally), Qdrant (Vector Store), Neo4j (Knowledge Graph)
* **AI / ML Services (Local):** 
    * **LLM Inference:** Ollama 
    * **Audio Transcription:** Whisper ASR
    * **Text-to-Speech:** Coqui TTS

---

## 💻 Prerequisites

Before you begin, ensure you have the following installed:

- [Python](https://www.python.org/downloads/) - Required to run the setup script
- [Git](https://git-scm.com/downloads/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) - Required to run all services. **Ensure WSL 2 integration is enabled on Windows.**

---

## 🏁 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/coleam00/local-ai-packaged.git
cd local-ai-packaged
```

### 2. Configure Environment Variables
Make a copy of `.env.example` and rename it to `.env` in the root directory.

Generate secure random values and fill in required secrets (do NOT use example strings in production):
- N8N secrets (`N8N_ENCRYPTION_KEY`, `N8N_USER_MANAGEMENT_JWT_SECRET`)
- Supabase secrets (`POSTGRES_PASSWORD`, `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`)
- Langfuse and Clickhouse passwords

> [!IMPORTANT]
> **Supabase Updates:** The latest Supabase containers require specific variables. Make sure your `.env` includes `POOLER_DB_POOL_SIZE=5`. Additionally, for the latest storage-api, include `GLOBAL_S3_BUCKET=stub`, `REGION=stub`, `STORAGE_TENANT_ID=stub`, `S3_PROTOCOL_ACCESS_KEY_ID`, and `S3_PROTOCOL_ACCESS_KEY_SECRET`.

### 3. Start the Services
The project includes a `start_services.py` script that manages starting both Supabase and the local AI services. It supports pulling models like `qwen3:8b-q4_K_M` and `nomic-embed-text` automatically.

Run the appropriate command for your hardware:

**For Nvidia GPU users (Recommended):**
```bash
python start_services.py --profile gpu-nvidia
```

**For AMD GPU users on Linux:**
```bash
python start_services.py --profile gpu-amd
```

**For Mac / CPU-only users:**
```bash
python start_services.py --profile cpu
```
*(If you run Ollama locally on your Mac instead of in Docker, use `--profile none` and set `OLLAMA_HOST=host.docker.internal:11434` in `docker-compose.yml`.)*

### 4. Apply Supabase Migrations
For InsightsLM to function properly, apply the necessary database tables:
1. Access the local Supabase dashboard at [http://localhost:8000](http://localhost:8000).
2. Navigate to the SQL Editor.
3. Paste the contents of `DocAns/supabase-migration.sql` and run it.

---

## 🧩 Importing Starter Workflows

You can import pre-built n8n workflows for DocAns:

1. Open n8n at [http://localhost:5678/](http://localhost:5678/). Create a local account.
2. Go to your workflow list, select **Import from File**.
3. Select the JSON files from the `n8n/backup/workflows/` or `DocAns/n8n/` folder.
4. Set up the necessary credentials for Supabase, Ollama, and Qdrant in n8n.
    - **Ollama URL:** `http://ollama:11434`
    - **Postgres Host:** `db` (use the credentials from your `.env`)

---

## 🌐 Accessing the Services

Once running, your local domains will immediately be available:

* **n8n Automation:** [http://localhost:5678](http://localhost:5678)
* **Open WebUI:** [http://localhost:3000](http://localhost:3000) (Configure N8N webhook via workspace functions)
* **InsightsLM Frontend:** [http://localhost:3010](http://localhost:3010)
* **Supabase Studio:** [http://localhost:8000](http://localhost:8000)
* **Flowise:** [http://localhost:3001](http://localhost:3001)

---

## 🔧 Troubleshooting

- **Supabase Analytics Startup Failure:** If the `supabase-analytics` container fails or is unhealthy (often occurs after changing Postgres passwords), delete the folder `supabase/docker/volumes/db/data` and restart the stack.
- **Docker Connection Errors:** If `start_services.py` crashes due to docker connection issues on Windows, make sure Docker Desktop is open and "Expose daemon on tcp://localhost:2375 without TLS" is turned on in Docker settings.
- **SearXNG Restarting:** If the SearXNG container keeps restarting, run `chmod 755 searxng` in your terminal to grant the necessary permissions for the `uwsgi.ini` file.
- **Login Error ("Invalid Authentication Credentials"):** Ensure in your `.env` that keys like `ANON_KEY` are not wrapped in quotes (e.g. `ANON_KEY=your-key-here`, not `ANON_KEY="your-key-here"`). If you change these keys, run `python start_services.py` with the `--build` flag manually appended to the docker up command inside the script.

## 📜 License

This codebase is distributed under the MIT/Apache 2.0 Licenses. Please note that n8n is distributed under a Sustainable Use License. Review the [n8n license](https://github.com/n8n-io/n8n/blob/master/LICENSE.md) if you are planning to use this in a commercial SaaS offering.

See the [LICENSE](LICENSE) file for details.
