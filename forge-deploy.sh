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
    # Reload user groups without logging out
    exec su -l $USER
fi

# Ensure ports 80 and 443 are available
sudo lsof -ti:80,443 | xargs -r sudo kill -9

# Stop any running containers
docker-compose down

# Remove old containers, networks, and volumes
docker-compose rm -f
docker network prune -f

# Build and start the containers
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check if containers are running
docker-compose ps

# Print the logs
docker-compose logs --tail=100

echo "Deployment completed successfully!"
echo "Services should be available at:"
echo "- https://calculator.unilog.company (Streamlit UI)"
echo "- https://api.calculator.unilog.company (FastAPI)"
