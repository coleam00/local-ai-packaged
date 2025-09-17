#!/bin/bash
set -e

# =============================================================================
# Docker CE Installation Script for Debian 12 (Root Version)
# =============================================================================

echo "Installing Docker CE on Debian 12..."

# Remove old Docker packages if they exist
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Update package list
apt update

# Install prerequisites
apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list

# Update package list with Docker repo
apt update

# Install Docker CE
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker service
systemctl start docker
systemctl enable docker

# Test Docker installation
docker --version
docker compose version

echo "Docker CE installed successfully!"
echo "Docker service is running and enabled."