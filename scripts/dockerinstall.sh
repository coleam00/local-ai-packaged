#!/bin/bash
set -e

echo "🚀 Starting full setup for local-ai-packaged on Debian 12..."

### 1. Install dependencies
echo "🔧 Installing system packages..."
apt update && apt install -y \
  curl \
  wget \
  git \
  python3 \
  python3-pip \
  unzip \
  ca-certificates \
  gnupg \
  lsb-release \
  software-properties-common

