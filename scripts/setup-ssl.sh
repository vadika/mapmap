#!/bin/bash
set -e

DOMAIN=${1:-yourdomain.com}
EMAIL=${2:-admin@yourdomain.com}

echo "🔒 Setting up SSL certificate for $DOMAIN..."

# Stop nginx container temporarily
cd /home/mapmap/mapmap
docker-compose -f docker-compose.production.yml stop nginx

# Get Let's Encrypt certificate
certbot certonly --standalone \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN

# Copy certificates to ssl directory
mkdir -p /home/mapmap/mapmap/ssl
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /home/mapmap/mapmap/ssl/cert.pem
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /home/mapmap/mapmap/ssl/key.pem
chown mapmap:mapmap /home/mapmap/mapmap/ssl/*

# Update nginx configuration
sed -i "s/yourdomain.com/$DOMAIN/g" /home/mapmap/mapmap/nginx-ssl.conf
cp /home/mapmap/mapmap/nginx-ssl.conf /home/mapmap/mapmap/nginx.conf

# Restart services with SSL
docker-compose -f docker-compose.production.yml up -d

echo "✅ SSL certificate installed successfully!"
echo "🌐 Service available at: https://$DOMAIN"

# Setup auto-renewal
echo "⏰ Setting up certificate auto-renewal..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'cd /home/mapmap/mapmap && docker-compose -f docker-compose.production.yml restart nginx'") | crontab -