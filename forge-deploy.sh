#!/bin/bash

# Exit on error
set -e

# Print each command
set -x

# Go to project directory
cd /home/forge/calculator.unilog.company

# Pull the latest changes
git pull origin main

# Create necessary directories if they don't exist
mkdir -p data

# Copy the .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Ensure docker and docker-compose are installed
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Add forge user to docker group if not already added
if ! groups forge | grep &>/dev/null '\bdocker\b'; then
    sudo usermod -aG docker forge
fi

# Stop any running containers
docker-compose down

# Build and start the containers
docker-compose build --no-cache
docker-compose up -d

# Prune unused images and volumes
docker image prune -f
docker volume prune -f

# Check if containers are running
docker-compose ps

# Print the logs
docker-compose logs --tail=100

echo "Deployment completed successfully!"
