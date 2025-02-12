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
mkdir -p logs/traefik

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

# Check if required ports are available
echo "Checking if required ports are available..."
for port in 8080 9444 9001 8001 8502; do
    if lsof -i ":$port" > /dev/null; then
        echo "Port $port is already in use. Stopping process..."
        sudo lsof -i ":$port" | awk 'NR!=1 {print $2}' | xargs sudo kill -9
    fi
done

# Thorough Docker cleanup
echo "Performing thorough Docker cleanup..."

# Stop all containers
echo "Stopping all containers..."
docker stop $(docker ps -a -q) 2>/dev/null || true

# Remove all containers
echo "Removing all containers..."
docker rm $(docker ps -a -q) 2>/dev/null || true

# Remove all networks
echo "Removing all networks..."
docker network rm $(docker network ls -q) 2>/dev/null || true

# Remove all volumes
echo "Removing all volumes..."
docker volume rm $(docker volume ls -q) 2>/dev/null || true

# Remove any hanging images
echo "Removing unused images..."
docker system prune -af

# Build and start the containers
echo "Building and starting containers..."
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check if containers are running
docker-compose ps

# Print the logs
echo "Traefik Logs:"
docker-compose logs traefik

echo "Deployment completed successfully!"
echo "Services should be available at:"
echo "- https://calculator.unilog.company:9444 (Streamlit UI)"
echo "- https://api.calculator.unilog.company:9444 (FastAPI)"
echo "- http://your-server-ip:9001 (Traefik Dashboard)"

# Monitor logs for SSL issues
echo "Monitoring Traefik logs for SSL issues..."
docker-compose logs -f traefik
