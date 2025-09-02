# Stop all running containers
docker stop $(docker ps -aq) 2>/dev/null

# Remove all containers
docker rm -f $(docker ps -aq) 2>/dev/null

# Remove all images
docker rmi -f $(docker images -aq) 2>/dev/null

# Remove all volumes
docker volume rm $(docker volume ls -q) 2>/dev/null

# Remove all networks (except default ones)
docker network rm $(docker network ls -q) 2>/dev/null

# Remove build cache
docker builder prune -af
