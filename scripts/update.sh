#!/bin/bash
# Code update script
set -e

cd /opt/smarthr

echo "=== SmartHR Update ==="

# 1. Backup database
echo "Backing up database..."
bash scripts/backup.sh

# 2. Pull latest code
echo "Pulling latest code..."
git pull

# 3. Rebuild frontend
echo "Building frontend..."
cd frontend && npm install && npm run build && cd ..

# 4. Rebuild and restart api container
echo "Rebuilding api container..."
docker compose up -d --build api

# 5. Run seed (in case new users added)
docker compose exec api python seed.py

echo "=== Update Complete ==="
