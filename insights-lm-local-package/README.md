# InsightsLM: Fully Local & Private Version

<p align="center">
  <img src="https://www.theaiautomators.com/wp-content/uploads/2025/07/Group-2651.svg" alt="InsightsLM Logo" width="600"/>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/theaiautomators/insights-lm-public?style=social)](https://github.com/theaiautomators/insights-lm-public/stargazers)
[![YouTube Video](https://img.shields.io/badge/YouTube-red)](https://www.youtube.com/watch?v=aj2FkaaL1co)

This repository contains the files and instructions needed to run a **fully local, private, and self-hosted** version of [InsightsLM](https://github.com/theaiautomators/insights-lm-public). Now, you can run your own AI research assistant completely offline, ensuring total privacy and control over your data.

This project builds upon the incredible work of **Cole Medin** and his [local-ai-packaged](https://github.com/coleam00/local-ai-packaged) repository, which provides the core self-hosted infrastructure.

---

## About The Project

While the original InsightsLM connects to cloud services, this version has been re-architected to run entirely on your local machine. It's the perfect solution for individuals and companies looking to leverage AI for internal knowledge management without relying on external cloud infrastructure.

The backend, powered by **N8N**, has been re-engineered to work with local models for inference, embeddings, transcription, and text-to-speech, all without requiring any changes to the frontend application.

<p align="center">
  <img src="https://www.theaiautomators.com/wp-content/uploads/2025/07/Group-2652.png" alt="The AI Automators Logo" width="500"/>
</p>

---

## Key Features

* **Run Completely Offline:** All services run locally in Docker containers. Your data never leaves your machine.
* **Chat with Your Documents:** Upload PDFs, text files, and audio files to get instant, context-aware answers from a local LLM.
* **Verifiable Citations:** Jump directly to the source of the information within your documents to verify the AI's responses.
* **Local Podcast Generation:** Create audio summaries from your source materials using local text-to-speech models.
* **Local Audio Transcription:** Transcribe audio files using a local Whisper container.
* **Total Control & Privacy:** You have complete control over the entire stack, from the models to the data.

---

## Demo & Walkthrough

For a full demonstration of this local version, an overview of its architecture, and a step-by-step guide on how to set it up, check out our YouTube video:

<p>
  <a target="_blank" href="https://www.youtube.com/watch?v=aj2FkaaL1co"><img src="https://raw.githubusercontent.com/theaiautomators/insights-lm-local-package/refs/heads/main/local.png" alt="Video" width="500"/></a>
</p>

---

## Architecture & Built With

This project runs a suite of services locally using Docker. The core components include:

* **Frontend App:**
    * [React](https://react.dev/) / [Vite](https://vitejs.dev/) / [TypeScript](https://www.typescriptlang.org/)
* **Backend & Automation:**
    * [N8N](https://n8n.io/)
* **Database & Storage:**
    * [Supabase](https://supabase.com/) (running locally)
* **AI / ML Services (Local):**
    * **LLM Inference & Embeddings:** [Olama](https://olama.com/) (using models like `qwen3:8b-q4_K_M`)
    * **Audio Transcription:** [Whisper ASR](https://github.com/ahmetoner/whisper-asr-webservice)
    * **Text-to-Speech:** [Coqui TTS](https://github.com/coqui-ai/TTS)

---

## Getting Started: Step-by-Step Installation

This guide provides the steps to get the fully local version of InsightsLM up and running.

I recommend you follow along from **10:48** in our [YouTube video](https://www.youtube.com/watch?v=aj2FkaaL1co) for a detailed visual guide.

### Prerequisites

* [Python](https://www.python.org/downloads/)
* [Git](https://git-scm.com/downloads/) or GitHub Desktop
* [Docker](https://www.docker.com/products/docker-desktop/) or Docker Desktop
* A code editor like [VS Code](https://code.visualstudio.com/) is highly recommended.

### Installation Steps

1.  **Clone the Base Local AI Package Repo**
    * Open your terminal or VS Code and clone Cole Medin's [local-ai-packaged](https://github.com/coleam00/local-ai-packaged) repository. This forms the foundation of our local setup.
    ```bash
    git clone https://github.com/coleam00/local-ai-packaged.git
    cd local-ai-packaged
    ```

2.  **Clone the InsightsLM Local Package**
    * Inside the `local-ai-packaged` directory, clone this repository.
    ```bash
    git clone https://github.com/theaiautomators/insights-lm-local-package.git
    ```

3.  **Configure Environment Variables**
    * In the root of the `local-ai-packaged` directory, make a copy of `.env.example` and rename it to `.env`.
    * Populate the necessary secrets (n8n secrets, postgres password, etc.) as described in Cole's repo. You can use a password generator for secure keys.
    * Generate the Supabase `JWT_SECRET`, `ANON_KEY`, and `SERVICE_ROLE_KEY` using the instructions in the documentation.
    * Open the `.env.copy` file located in `insights-lm-local-package/` and copy all the variables from it.
    * Paste these new variables at the end of your main `.env` file. These include URLs for the local services and a webhook auth key which you need to set.

4.  **Update Docker Compose**
    * Open the main `docker-compose.yml` file in the root directory.
    * Open the `docker-compose.yml.copy` file located inside `insights-lm-local-package/`.
    * Copy the `whisper-cache` volume and the three services (`insights-lm`, `coqui-tts`, `whisper-asr`) from the `.copy` file. 
    * Paste them into the main `docker-compose.yml` file in their respective `volumes` and `services` sections.
    * Note: Both Coqui and Whisper are configured in these services to work on a GPU. If you are using Apple Silicon or a CPU then check out their respective documentation on how adjust these.
    * Update the Olama model to `qwen3:8b-q4_K_M` on line 55.

5.  **Start the Services**
    * Open up Docker Desktop
    * Run the start script provided in Cole's repository. Use the command appropriate for your system (e.g., Nvidia GPU). This will download all the necessary Docker images and start the containers. This may take a while.
    ```bash
    # Example for Nvidia GPU
    python start_services.py --profile gpu-nvidia
    ```

6.  **Import Supabase Script**
    * Login to your Supabase instance (usually at `http://localhost:8000`)
    * Go to SQL Editor
    * Paste the contents of the file located in `insights-lm-local-package/supabase-migration.sql` into the SQL editor and click Run
    * You should get a "Success. No rows returned" message

7.  **Move Supabase Functions**
    * Once the Docker images have downloaded and the service are up, navigate to the `insights-lm-local-package/supabase/functions/` directory.
    * Copy all the function folders within it.
    * Paste them into the `supabase/volumes/functions/` directory.

8.  **Update Supabase Docker Configuration**
    * Open the `supabase/docker/docker-compose.yml` file.
    * Copy the environment variables listed in `insights-lm-local-package/supabase/docker-compose.yml.copy`.
    * Paste these variables under the `functions` service in the `supabase/docker/docker-compose.yml` file. This gives the edge functions access to your N8N webhook URLs.

9.  **Restart Docker Containers**
    * Shut down all running services using the provided command.
    ```bash
    # Example for Nvidia GPU
    docker compose -p localai -f docker-compose.yml --profile gpu-nvidia down
    ```
    * Restart the services using the `start_services.py` script again to apply all changes.



9.  **Import and Configure N8N Workflows**
    * Access N8N in your browser (usually at `http://localhost:5678`).
    * Create a new workflow and import the `Import_Insights_LM_Workflows.json` file from the `insights-lm-local-package/n8n/` directory.
    * Follow the steps in the video to configure the importer workflow.
        * Create an N8N API Key and set the credential in the N8N node
            * URL should be "http://localhost:5678/api/v1"
        * Create credential for Webhook Header Auth and copy the credential ID into the "Enter User Values" node
            * Name must be "Authorization" and value is what was set at the bottom of the ENV file 
        * Create credential for Supabase API and copy the credential ID into the "Enter User Values" node
            * Host should be "http://kong:8000"
            * Service Role Secret is in your ENV file
        * Create credential for Olama and copy the credential ID into the "Enter User Values" node 
            * Base URL should be "http://ollama:11434"
    * Run the importer workflow to automatically set up all the required InsightsLM workflows in your N8N instance.

10. **Activate Workflows & Test**
    * Go to your N8N dashboard, find the newly imported workflows, and activate them all (Except the "Extract Text" workflow).
    * Access the InsightsLM frontend (usually at `http://localhost:3010`).
    * Create a user in your local Supabase dashboard (under Authentication) to log in.
    * You're all set! Start uploading documents and chatting with your private AI assistant.

---

## Contributing

Contributions make the open-source community an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

* Fork the Project
* Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
* Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
* Push to the Branch (`git push origin feature/AmazingFeature`)
* Open a Pull Request

---

## License

This codebase is distributed under the MIT License.

---

## A Note on n8n's Sustainable Use License

While InsightsLM is fully open-sourced and Supabase is also open source, it's important to be aware that n8n, which powers much of the backend automation, is not open source in the traditional sense.

n8n is distributed under a [Sustainable Use License](https://github.com/n8n-io/n8n/blob/master/LICENSE.md). This license allows free usage for internal business purposes, including hosting workflows within your company or organization.

However, if you plan to use InsightsLM as part of a commercial SaaS offering—such as reselling access or hosting a public version for multiple clients—you may need to obtain an n8n Enterprise License. We’re not lawyers, so we recommend that you review the n8n license and contacting their team if your use case falls into a commercial category.

Alternatives: If your use case is restricted by the n8n license, one potential option is to convert key workflows into Supabase Edge Functions. This would allow you to fully avoid using n8n in production.

---

## Frequently Asked Questions (FAQ)

### Upload Error on macOS with Docker Desktop

**Problem:** Getting "Upload Error. Failed to upload document X. Please try again." when uploading documents, pasting text, or submitting links on macOS.

**Solution:** This issue is related to Docker volume mounting on macOS. Use a named volume instead of bind-mount.

Note: This solution was provided by a user in a comment on Youtube. I haven't independently verified it.

**Required changes:**

1. **Update the storage service in your `docker-compose.yml`:**
   ```yaml
   services:
     storage:
       image: supabase/storage-api:v1.25.7
       volumes:
         - supabase_storage_data:/var/lib/storage
   ```

2. **Update the imgproxy service (if it also uses a bind-mount):**
   ```yaml
   services:
     imgproxy:
       image: darthsim/imgproxy:v3.8.0
       volumes:
         - supabase_storage_data:/var/lib/storage
   ```

3. **At the bottom of your `docker-compose.yml`, declare the volume:**
   ```yaml
   volumes:
     supabase_storage_data:
   ```

**Restart with clearing old data:**

Since the bind-mount is still on `./volumes/storage`, the previous containers and mounts need to be removed before bringing it up again:

```bash
docker compose -p localai -f docker-compose.yml --profile none down -v --remove-orphans   
```

Finally, restart the service and the issue will be resolved:

```bash
python3 start_services.py --profile none
```

### LangFuse Encryption Error

**Problem:** Getting encryption errors when using Langfuse.

**Solution:** You need to use OpenSSL to generate the encryption key properly. This is required in the ENV file:

```bash
############
# [required]
# Langfuse credentials
# Each of the secret keys you can set to whatever you want, just make it secure!
# For the encryption key, use the command `openssl rand -hex 32`
#   openssl is available by default on Linux/Mac
#   For Windows, you can use the 'Git Bash' terminal installed with git
############

CLICKHOUSE_PASSWORD=super-secret-key-1
MINIO_ROOT_PASSWORD=super-secret-key-2
LANGFUSE_SALT=super-secret-key-3
NEXTAUTH_SECRET=super-secret-key-4
ENCRYPTION_KEY=generate-with-openssl # generate via `openssl rand -hex 32`
```

**Note:** Langfuse isn't actually needed to get this working, so it's likely not the cause of upload issues.

### Login Error - "Invalid Authentication Credentials"

**Problem:** Getting "invalid authentication credentials" error when trying to log in.

**Solution 1.**

It can be caused by having quotes in the environment files. Check your `.env` file and make sure you haven't wrapped the `ANON_KEY` or `SERVICE_ROLE_KEY` in quotes.

**Incorrect:**
```bash
SUPABASE_ANON_KEY="your-key-here"
SUPABASE_SERVICE_ROLE_KEY="your-key-here"
```

**Correct:**
```bash
SUPABASE_ANON_KEY=your-key-here
SUPABASE_SERVICE_ROLE_KEY=your-key-here
```

**Solution 2.**

If you have made changes to the SUPABASE_ANON_KEY in your ENV file after initial setup, then you need to rebuild your InsightsLM container.

For this, go to the start_service.py file

Change line 77 from this

    cmd.extend(["up", "-d"])

to this

    cmd.extend(["up", "-d", "--build"])

Then trigger the start services command with your selected profile

python start_services.py --profile <your-profile>

This will take down any containers that are currently up and then rebuild the existing containers so they have the updated ENVs loaded in

### "Failed to Fetch" Error

If the wrong Anon Key or Project URL was set, the login screen would throw a "Failed to Fetch" error

### Audio Deep Dive Feature Limitation

**Important Note:** The audio deep dive feature with 2 hosts doesn't actually work on the local version. You'd need to use the cloud version that integrates with Google TTS to access this functionality.

### Document OCR Support

**Current Limitation:** This system doesn't currently perform OCR on documents - it only extracts text from machine-readable PDFs.

**Workaround:** You could integrate Docling for OCR functionality. Check out Alan's video on our channel where he demonstrates using Docling locally: [https://www.youtube.com/watch?v=eHw_6jhK8AM](https://www.youtube.com/watch?v=eHw_6jhK8AM)