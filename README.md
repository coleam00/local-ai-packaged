# Pack d’IA auto-hébergé

**Pack d’IA auto-hébergé** est un modèle open-source basé sur Docker Compose qui vous permet de déployer en quelques minutes un environnement complet de développement Local AI et low-code. Il inclut :

- **Ollama** pour vos modèles LLM locaux  
- **Open WebUI** pour dialoguer avec vos agents n8n  
- **Supabase** pour la base de données, le vector store et l’authentification  

Cette version, maintenue par Cole, apporte plusieurs améliorations et ajoute Supabase, Open WebUI, Flowise, Langfuse, SearXNG et Caddy. Les workflows RAG AI Agent présentés dans la vidéo seront automatiquement importés dans votre instance n8n.

---

## Liens importants

- [Communauté Local AI](https://thinktank.ottomator.ai/c/local-ai/18) (oTTomator Think Tank)  
- [Tableau Kanban GitHub](https://github.com/users/coleam00/projects/2/views/1) pour le suivi des fonctionnalités et corrections  
- [Local AI Starter Kit d’origine](https://github.com/n8n-io/self-hosted-ai-starter-kit) par l’équipe n8n  
- Téléchargez mon intégration N8N + Open WebUI [directement sur le site Open WebUI](https://openwebui.com/f/coleam/n8n_pipe/) (instructions ci-dessous)

![n8n.io - Capture d’écran](https://raw.githubusercontent.com/n8n-io/self-hosted-ai-starter-kit/main/assets/n8n-demo.gif)

Conçu par <https://github.com/n8n-io> et <https://github.com/coleam00>, ce pack combine la plateforme n8n auto-hébergée avec une liste d’outils IA compatibles pour démarrer rapidement vos workflows IA.

### Ce qui est inclus

✅ [**n8n auto-hébergé**](https://n8n.io/) – Plate-forme low-code avec plus de 400 intégrations et composants IA  
✅ [**Supabase**](https://supabase.com/) – Base de données open-source en tant que service, très utilisée pour les agents IA  
✅ [**Ollama**](https://ollama.com/) – Plate-forme cross-platform pour installer et exécuter des LLM locaux  
✅ [**Open WebUI**](https://openwebui.com/) – Interface ChatGPT-like pour interagir en privé avec vos modèles et agents n8n  
✅ [**Flowise**](https://flowiseai.com/) – Constructeur d’agents IA no/low-code, complémentaire à n8n  
✅ [**Qdrant**](https://qdrant.tech/) – Vector store haute performance avec API complète  
✅ [**SearXNG**](https://searxng.org/) – Méta-moteur de recherche libre, sans suivi utilisateur  
✅ [**Caddy**](https://caddyserver.com/) – Gestion automatique du HTTPS/TLS pour vos domaines  
✅ [**Langfuse**](https://langfuse.com/) – Plate-forme d’observabilité pour vos agents LLM  

---

## Prérequis

Avant de commencer, assurez-vous d’avoir installé :

- [Python](https://www.python.org/downloads/) – Nécessaire pour lancer le script d’installation  
- [Git / GitHub Desktop](https://desktop.github.com/) – Pour gérer le dépôt  
- [Docker / Docker Desktop](https://www.docker.com/products/docker-desktop/) – Pour exécuter tous les services  

---

## Installation

Clonez le dépôt et naviguez dans le dossier :

```bash
git clone https://github.com/coleam00/local-ai-packaged.git
cd local-ai-packaged

Avant de lancer les services, créez et éditez votre fichier d’environnement :

cp .env.example .env

Ouvrez .env et renseignez les variables suivantes :

############
# Configuration n8n
############
N8N_ENCRYPTION_KEY=
N8N_USER_MANAGEMENT_JWT_SECRET=

############
# Secrets Supabase
############
POSTGRES_PASSWORD=
JWT_SECRET=
ANON_KEY=
SERVICE_ROLE_KEY=
DASHBOARD_USERNAME=
DASHBOARD_PASSWORD=
POOLER_TENANT_ID=

############
# Identifiants Langfuse
############
CLICKHOUSE_PASSWORD=
MINIO_ROOT_PASSWORD=
LANGFUSE_SALT=
NEXTAUTH_SECRET=
ENCRYPTION_KEY=

IMPORTANT : générez des valeurs aléatoires et sécurisées pour tous les secrets. N’utilisez jamais les exemples en production.

Si vous déployez en production avec Caddy, décommentez et configurez :

############
# Configuration Caddy
############
N8N_HOSTNAME=n8n.votre-domaine.com
WEBUI_HOSTNAME=openwebui.votre-domaine.com
FLOWISE_HOSTNAME=flowise.votre-domaine.com
SUPABASE_HOSTNAME=supabase.votre-domaine.com
OLLAMA_HOSTNAME=ollama.votre-domaine.com
SEARXNG_HOSTNAME=searxng.votre-domaine.com
LETSENCRYPT_EMAIL=votre-email@example.com

Le projet inclut un script start_services.py qui démarre Supabase et les services locaux. Utilisez le flag --profile adapté à votre GPU :

Pour GPU Nvidia

python start_services.py --profile gpu-nvidia

Note : si vous n’avez jamais utilisé votre GPU Nvidia avec Docker, suivez les instructions Ollama Docker.

Pour GPU AMD (Linux)

python start_services.py --profile gpu-amd

Pour Mac / Apple Silicon

CPU uniquement :
python start_services.py --profile cpu

Ollama local + Mac :
python start_services.py --profile none

Pour Mac avec Ollama local (hors Docker)
Dans votre docker-compose.yml, sous la clé x-n8n :

x-n8n: &service-n8n
  # ... autres configurations ...
  environment:
    # ... autres variables ...
    - OLLAMA_HOST=host.docker.internal:11434

Ensuite, une fois l’interface accessible (http://localhost:5678/) :

Rendez-vous sur http://localhost:5678/home/credentials

Cliquez sur Local Ollama service

Modifiez l’URL de base en http://host.docker.internal:11434/

Pour tous les autres cas :

python start_services.py --profile cpu

Déploiement dans le Cloud
Prérequis
Machine Linux (Ubuntu recommandé) avec Nano, Git et Docker installés

Étapes supplémentaires
Ouvrez les ports requis :

sudo ufw enable
sudo ufw allow 80 443 3000 3001 3002 5678 8000 8080 11434
sudo ufw reload

Configurez vos enregistrements DNS de type A pour chaque sous-domaine (n8n, Open WebUI, etc.) vers l’IP de votre serveur.

Démarrage rapide et utilisation
Ouvrez http://localhost:5678/ dans votre navigateur pour configurer n8n (une seule fois).

Chargez le workflow fourni : http://localhost:5678/workflow/vTN9y2dLXqTiDfPT

Créez les identifiants :

Ollama URL : http://ollama:11434

Postgres (Supabase) : hôte db, identifiants issus de .env

Qdrant URL : http://qdrant:6333 (API key libre)

Google Drive : suivez le guide n8n

Cliquez sur Test workflow pour lancer l’exécution.

À la première exécution, patientez le temps du téléchargement de Llama3.1.

Activez le workflow et copiez l’URL du webhook Production.

Ouvrez http://localhost:3000/ pour configurer Open WebUI.

Dans Workspace → Functions, cliquez sur Add Function :

Saisissez un nom et une description

Collez le code de n8n_pipe.py

Dans les paramètres, définissez n8n_url sur l’URL du webhook copié, puis activez la fonction.

Vous avez désormais accès à plus de 400 intégrations et à des nœuds IA (Agent, Text classifier, Information Extractor). Pour rester en local, utilisez le nœud Ollama et Qdrant.


Mise à jour

# Arrêter tous les services
docker compose -p localai --profile <votre-profil> \
  -f docker-compose.yml -f supabase/docker/docker-compose.yml down

# Télécharger les dernières images
docker compose -p localai --profile <votre-profil> \
  -f docker-compose.yml -f supabase/docker/docker-compose.yml pull

# Relancer avec votre profil
python start_services.py --profile <votre-profil>

Dépannage
Problèmes Supabase
supabase-pooler redémarre en boucle : suivez cette issue.

supabase-analytics n’arrive pas à démarrer : supprimez le dossier supabase/docker/volumes/db/data.

Docker Desktop : activez « Expose daemon on tcp://localhost:2375 without TLS ».

Service Supabase indisponible : évitez le caractère @ dans le mot de passe Postgres.

Problèmes GPU
Windows GPU : dans Docker Desktop, activez le backend WSL 2 et consultez la doc GPU Docker.

Linux GPU : suivez les instructions Ollama Docker.

Lectures recommandées
Agents IA pour développeurs : théorie et pratique (n8n)

Tutoriel : construire un workflow IA dans n8n

Concepts Langchain dans n8n

Comparatif : Agents vs Chains

Qu’est-ce qu’une base vectorielle ?

🎥 Vidéo de présentation
Guide de Cole pour le Local AI Starter Kit

🛍️ Galerie de templates IA
https://n8n.io/workflows/?categories=AI

AI Agent Chat

AI chat avec source de données

Chat avec OpenAI Assistant (mémoire)

LLM open-source (HuggingFace)

Chat avec PDF (citation)

Agent de scraping

Conseils & astuces
Accès aux fichiers locaux
Le dossier partagé monté dans le conteneur n8n (/data/shared) permet de :

Lire/écrire des fichiers (Read/Write Files from Disk)

Déclencher à partir de fichiers locaux (Local File Trigger)

Exécuter des commandes (Execute Command)

📜 Licence
Ce projet (initialement créé par l’équipe n8n) est sous licence Apache 2.0.
Voir le fichier LICENSE pour plus de détails.
