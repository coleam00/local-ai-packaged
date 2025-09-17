#!/bin/bash
set -e

# =============================================================================
# Debian 12 Software Package Installation Script (Root Version)
# Installs only the software packages needed - nothing else
# =============================================================================

echo "Installing required software packages..."

# Update package list
apt update

# Install ALL required packages
apt install -y \
    sudo \
    git \
    curl \
    wget \
    ca-certificates \
    gnupg \
    lsb-release \
    apt-transport-https \
    software-properties-common \
    openssl \
    pwgen \
    nano \
    vim \
    htop \
    tree \
    net-tools \
    netcat-openbsd \
    unzip \
    jq \
    python3 \
    python3-pip \
    python3-venv

# Upgrade pip
python3 -m pip install --upgrade pip

# Install Python packages for start_services.py
python3 -m pip install requests

echo "Done. All software packages installed."
echo "Note: You still need to install Docker separately."