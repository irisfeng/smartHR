#!/bin/bash
# SmartHR ECS first-time deployment script
set -e

echo "=== SmartHR First-Time Deployment ==="

# 1. Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
    echo "Docker installed."
fi

# 2. Format and mount data disk (/dev/vdb)
if ! mountpoint -q /data; then
    if ! blkid /dev/vdb &>/dev/null; then
        echo "Formatting data disk..."
        mkfs.ext4 /dev/vdb
    fi
    mkdir -p /data
    mount /dev/vdb /data
    grep -q '/dev/vdb' /etc/fstab || echo "/dev/vdb /data ext4 defaults 0 2" >> /etc/fstab
    echo "Data disk mounted at /data"
fi
mkdir -p /data/{postgres,uploads,backups}

# 3. Setup environment variables
cd /opt/smarthr
if [ ! -f .env ]; then
    cp .env.production .env
    SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
    sed -i "s|SECRET_KEY=change-me|SECRET_KEY=${SECRET}|" .env
    chmod 600 .env
    echo ""
    echo "Please edit .env and fill in:"
    echo "  - POSTGRES_PASSWORD"
    echo "  - ALLOWED_ORIGINS (your ECS public IP)"
    echo "  - MINERU_API_KEY"
    echo "  - AI_API_KEY"
    echo ""
    echo "  nano /opt/smarthr/.env"
    echo ""
    echo "Then re-run this script."
    exit 0
fi

# 4. Build frontend
echo "Building frontend..."
cd frontend
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
fi
npm install && npm run build
cd ..

# 5. Start services
echo "Starting services..."
docker compose up -d --build

# 6. Wait for DB, seed users
echo "Waiting for database..."
sleep 5
docker compose exec api python seed.py

# 7. Setup daily backup cron
(crontab -l 2>/dev/null | grep -v 'smarthr.*backup' ; echo "0 3 * * * cd /opt/smarthr && bash scripts/backup.sh >> /data/backups/cron.log 2>&1") | crontab -
echo "Daily backup cron configured (3:00 AM)."

echo ""
echo "=== Deployment Complete ==="
echo "Access: https://$(curl -s ifconfig.me)"
echo ""
echo "Default password: Smart2026! (change immediately)"
echo "  HR: hr"
echo "  Managers: mgr_delivery, mgr_rd, mgr_marketing, mgr_ops1, mgr_ops2,"
echo "            mgr_sales1, mgr_sales2, mgr_finance, mgr_hr"
