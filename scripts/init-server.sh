#!/bin/bash
# Server initialization script for MapMap
# This script is run by cloud-init during VPS setup

set -e

echo "🚀 Initializing MapMap server..."

# Update system
apt-get update
apt-get upgrade -y

# Configure firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable docker
systemctl start docker

# Install Docker Compose standalone
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add mapmap user to docker group
usermod -aG docker mapmap

# Clone MapMap repository
cd /home/mapmap
if [ ! -d "mapmap" ]; then
    git clone https://github.com/vadika/mapmap.git
fi
chown -R mapmap:mapmap /home/mapmap/mapmap

# Setup production environment
cd /home/mapmap/mapmap
if [ ! -f ".env" ]; then
    cp .env.production .env
    chown mapmap:mapmap .env
fi

# Create directories
mkdir -p logs ssl
chown -R mapmap:mapmap logs ssl

# Make scripts executable
chmod +x scripts/*.sh

# Configure fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# Enable MapMap systemd service
systemctl daemon-reload
systemctl enable mapmap
systemctl start mapmap

echo "✅ Server initialization complete!"
echo "📝 Next steps:"
echo "   1. Update /home/mapmap/mapmap/.env with your settings"
echo "   2. Run: sudo -u mapmap /home/mapmap/mapmap/scripts/setup-ssl.sh yourdomain.com"