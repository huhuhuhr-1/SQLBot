#!/bin/bash
# Script to configure Docker with image accelerator for China region

# Check if Docker daemon.json exists, create if not
if [ ! -f /etc/docker/daemon.json ]; then
    sudo mkdir -p /etc/docker
    echo '{}' | sudo tee /etc/docker/daemon.json
fi

# Backup original daemon.json
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%s)

# Configure Docker with mirror accelerators
echo '{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.ccs.tencentyun.com",
    "https://ccr.ccs.tencentyun.com"
  ],
  "insecure-registries": [],
  "debug": false,
  "experimental": false
}' | sudo tee /etc/docker/daemon.json

# Restart Docker service
sudo systemctl restart docker

echo "Docker configured with image accelerators. Please try running the Sealos script again."