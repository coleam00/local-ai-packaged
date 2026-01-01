# Management UI Quickstart Guide

The Management UI provides a web-based interface for configuring and monitoring your Local AI stack.

## Starting the Management UI

### Option 1: Using Docker Compose (Recommended)

```bash
docker compose -p localai build management-ui
docker compose -p localai up -d management-ui
```

### Option 2: Manual Docker Run

```bash
# Build the image
docker build -t localai-management:latest management-ui/

# Run the container
docker run -d \
  --name localai-management \
  --restart unless-stopped \
  -p 127.0.0.1:9999:9000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd):/config" \
  localai-management:latest
```

**Windows users:** Replace `$(pwd)` with the full path to your project directory.

## Accessing the UI

Open your browser and navigate to:

```
http://localhost:9999
```

## Setup Wizard

On first launch, you'll be guided through a 7-step setup wizard:

### Step 1: Preflight Check
Verifies Docker is running and checks for potential issues.

### Step 2: Profile Selection
Choose your hardware profile:
- **CPU Only** - Run models on CPU (slower but universal)
- **NVIDIA GPU** - Use NVIDIA GPU acceleration (requires NVIDIA Docker runtime)
- **AMD GPU** - Use AMD GPU with ROCm
- **External Ollama** - Connect to an existing Ollama instance

### Step 3: Service Selection
Choose which services to enable:

| Service | Description |
|---------|-------------|
| Open WebUI | Chat interface for LLMs |
| Flowise | Visual LLM flow builder |
| n8n | Workflow automation |
| Qdrant | Vector database |
| Neo4j | Graph database |
| Langfuse | LLM observability |
| SearXNG | Privacy-focused search |

Services you don't select won't be started or shown in the dashboard.

### Step 4: Port Configuration
Customize port mappings if defaults conflict with existing services.

### Step 5: Environment
Choose deployment mode:
- **Private (localhost)** - Exposes ports on 127.0.0.1 only
- **Public (HTTPS)** - For production with Caddy reverse proxy

### Step 6: Secrets
Configure API keys and passwords:
- Generate random secrets automatically
- Or enter your own values

### Step 7: Confirm & Save
Review your configuration and save it.

## Starting Services

After the wizard completes, you'll see a CLI command to run:

```bash
python start_services.py --profile cpu --environment private
```

**Important:** Run this command from your terminal (not from the UI). This ensures proper Docker volume mounting and database initialization.

The script will:
1. Clone/update the Supabase repository
2. Generate any missing secrets
3. Start Supabase services first
4. Wait for Supabase to initialize
5. Start your selected Local AI services

## Dashboard

After services are running, the dashboard shows:

- **Service Status** - Running/stopped count
- **Health** - Healthy service count
- **Quick Actions** - Start/stop/restart individual services

### Filtering
The dashboard only shows services you enabled during setup. If you selected 5 services, you'll only see those 5.

## Services Page

Navigate to **Services** for detailed management:

- **Grouped View** - Services organized by category
- **List View** - Flat list of all services
- **Search** - Filter by name or group
- **Group Actions** - Start/stop all services in a group

## Reconfiguring

To change your configuration:

1. Delete the Management UI database:
   ```bash
   docker exec localai-management rm /app/data/management.db
   ```

2. Restart the container:
   ```bash
   docker restart localai-management
   ```

3. The setup wizard will appear again.

Alternatively, edit `.stack-config.json` directly and re-run `start_services.py`.

## Troubleshooting

### Services not showing in wizard
Ensure the project directory is mounted to `/config`:
```bash
docker run ... -v "$(pwd):/config" ...
```

### "Not authenticated" errors
The Management UI uses a simple authentication system. Clear your browser cookies or use an incognito window.

### Services not starting
Run `start_services.py` from your host terminal, not from within Docker. This ensures proper path resolution for volume mounts.

### Dashboard shows all services instead of selected ones
Verify your stack config was saved:
```bash
curl http://localhost:9999/api/setup/stack-config
```

Should return your configuration with `enabled_services` array.

## Architecture

```
+-------------------+     +-------------------+
|  Management UI    |     |  start_services.py|
|  (Docker)         |     |  (Host)           |
+-------------------+     +-------------------+
         |                         |
         v                         v
+-------------------+     +-------------------+
| .stack-config.json| <-- | Read config       |
| (Host filesystem) |     | Start containers  |
+-------------------+     +-------------------+
         |
         v
+-------------------+
| Docker Compose    |
| Services          |
+-------------------+
```

The Management UI writes configuration files to the host filesystem. The `start_services.py` script reads these files and starts Docker containers with proper volume mounts.

## Version

Check your Management UI version in the browser console or at the bottom of the dashboard.

Current version: **1.3.2**
