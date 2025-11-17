You are an expert software engineer specializing in AI/RAG systems, Python development, and Docker orchestration. Your task is to perform a major refactoring of the local-ai-packaged repository.

  <objective>
  The primary objective is to upgrade the repository's architecture by integrating the new, advanced RAG system from the all-rag-strategies directory. This involves decoupling existing services, implementing a new database schema,
  updating the n8n workflow, and consolidating the Docker setup. Archon will be treated as a separate, modular service with its own database, while the main RAG system will use a local Supabase/Postgres instance.
  </objective>

  <context_files>
  This refactoring is based on the architecture and code described in the following key files. You must analyze them to understand the target state.

   - High-Level Architecture Guide:
     - @CLAUDE.md: The central document describing the target architecture. This file itself will need to be updated as the final step.
     - @all-rag-strategies/README.md: Overview of the new RAG strategies.
     - @all-rag-strategies/implementation/IMPLEMENTATION_GUIDE.md: Detailed guide to the RAG implementation.
     - @all-rag-strategies/implementation/STRATEGIES.md: Description of the implemented strategies.

   - New RAG Database Schema:
     - @all-rag-strategies/implementation/sql/schema.sql: The definitive schema for the new RAG Postgres database.

   - New RAG Core Logic (Python):
     - @all-rag-strategies/implementation/rag_agent_advanced.py: The core agent logic with multiple RAG strategies.
     - @all-rag-strategies/implementation/ingestion/ingest.py: The new data ingestion pipeline.
     - @all-rag-strategies/implementation/utils/db_utils.py: Database utilities.
     - @all-rag-strategies/implementation/utils/providers.py: LLM provider configuration.
     - @all-rag-strategies/implementation/utils/models.py: Pydantic data models.
     - @all-rag-strategies/implementation/cli.py: A CLI for interacting with the RAG agent.

   - New n8n Workflow:
     - @n8n_knowledge_graph_rag/RAG_AI_Agent_Template_V5.json: The new n8n workflow to be implemented.
     - @n8n_knowledge_graph_rag/README.md: Explanation of the new n8n workflow and its integration with a Knowledge Graph.

   - Docker & Environment Configuration:
     - @docker-compose.yml: The main docker-compose file to be updated.
     - @Archon/docker-compose.yml: The Archon docker-compose file to be integrated.
     - @all-rag-strategies/implementation/docker-compose.yml: A reference for the RAG service configuration.
     - @all-rag-strategies/implementation/env.example: The reference for the new .env variables.

   - Existing Files to be Updated/Replaced:
     - @start_services.py: The main service startup script.
     - @n8n_pipe.py: The pipe script for Open WebUI to communicate with n8n.
     - @/home/sedinha/Desktop/local-ai-packaged/Local_RAG_AI_Agent_n8n_Workflow.json: The old, deprecated n8n workflow.
     - @.env.example & @.env copy.example: Root environment example files.
  </context_files>

  <step_by_step_plan>
  Follow this plan sequentially to perform the refactoring.

  Step 1: Update Environment Configuration
   1. Analyze @all-rag-strategies/implementation/env.example to identify all required environment variables for the new RAG system.
   2. Merge the required variables into the root .env.example and .env copy.example files.
   3. Ensure variables for the new RAG database (Postgres), OpenAI, and the decoupled Archon database are present and clearly separated.
   4. Create a new .env file in supabase/docker/ based on supabase/docker/.env.example, ensuring it aligns with the root .env for the local RAG setup.

  Step 2: Update Supabase for Local RAG
   2. The db service within this file must be configured to initialize using the new database schema. Mount @all-rag-strategies/implementation/sql/schema.sql to the docker-entrypoint-initdb.d directory of the db service. This will create
      the documents and chunks tables for the RAG system.
   3. Reference @all-rag-strategies/implementation/docker-compose.yml to see how the postgres service is configured and apply similar logic to the db service in docker-compose.yml.

  Step 3: Integrate Advanced RAG Logic
   1. The file @all-rag-strategies/implementation/rag_agent_advanced.py is the new core logic. Given its advanced, multi-strategy nature and CLI capabilities, it should be kept as a standalone, powerful tool for developers and not replace
      a simpler script.
   2. Update start_services.py: Modify this script to correctly start the entire new stack as defined in the updated docker-compose files. It should handle the startup of the main services, the integrated Supabase services for RAG, and the
      modular Archon services.
   3. Update n8n_pipe.py: Analyze the new n8n workflow (RAG_AI_Agent_Template_V5.json) webhook structure. Update n8n_pipe.py to correctly call the new n8n webhook endpoint, passing the chatInput and sessionId as expected by the new
      workflow.

  Step 4: Update n8n Workflow
   1. Replace the contents of Local_RAG_AI_Agent_n8n_Workflow.json with the contents of n8n_knowledge_graph_rag/RAG_AI_Agent_Template_V5.json. This makes the new workflow the default for the project.

  Step 5: Consolidate Docker Compose
   1. Modify the root docker-compose.yml.
   2. It already includes Archon/docker-compose.yml. Verify that the service names do not conflict and that they can communicate over the default Docker network.
   3. Ensure the main docker-compose.yml correctly orchestrates the startup of all services: n8n, the local Supabase stack (for RAG), and the Archon stack. Archon should be configured to use its own cloud database as per @CLAUDE.md, while
      the RAG components (n8n, Python scripts) should point to the local Supabase db service.

  Step 6: Finalize and Document
   1. Review all changes for consistency.
   2. Update the main @CLAUDE.md document to reflect the new, successfully implemented architecture. The new documentation should explain:
       - The decoupled nature of Archon.
       - The new local RAG database powered by Supabase/Postgres with the pgvector schema.
       - The role of the all-rag-strategies implementation.
       - How to use the new n8n workflow and the advanced RAG CLI.
       - The updated .env configuration.
       - The correct command to start all services using start_services.py.
  </step_by_step_plan>

  <deliverables>
   - A set of file modifications (patches or new file contents) for all the files mentioned in the plan.
   - A completely updated @CLAUDE.md that serves as the new operational guide for the refactored project.
  </deliverables>

  <constraints>
   - Do not implement the RAG strategies that the user explicitly postponed (08-late-chunking, 09-hierarchical-rag, 10-self-reflective-rag, 11-fine-tuned-embeddings).
   - Archon must remain modular and use its own database configuration, separate from the RAG system's database.
   - The primary RAG database is the local Postgres instance managed by the Supabase Docker setup.
   - All changes must be reflected in the final docker-compose.yml and .env files.
  </constraints>