docker stop $(docker ps -aq) 2>/dev/null
docker rm -f $(docker ps -aq) 2>/dev/null

# Remove all images
docker rmi -f $(docker images -q) 2>/dev/null

# Remove all volumes
docker volume rm $(docker volume ls -q) 2>/dev/null

# Remove all networks (except the default ones: bridge, host, none)
docker network rm $(docker network ls -q | grep -vE '^(|[0-9a-f]{12})$' | grep -vE 'bridge|host|none') 2>/dev/null

# Prune everything just in case
docker system prune -a --volumes -f