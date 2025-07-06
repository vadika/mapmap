# VPS Deployment Guide

Deploy MapMap Tile Proxy on any VPS using cloud-init for automated setup.

## Quick Deployment

### 1. VPS Provider Setup

**Supported Providers:**
- DigitalOcean, Linode, Vultr, Hetzner, AWS EC2, Google Cloud, Azure

**Requirements:**
- Ubuntu 22.04 LTS or newer
- Minimum: 1 vCPU, 1GB RAM, 20GB storage
- Recommended: 2 vCPU, 2GB RAM, 40GB storage

### 2. Cloud-Init Deployment

#### Option A: Direct cloud-init (Most Providers)

1. **Copy the cloud-init configuration:**
   ```bash
   # Upload cloud-init.yaml to your VPS provider
   ```

2. **SSH key is automatically included from your ~/.ssh:**
   ```bash
   # Your SSH key is already configured:
   # ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJKQ+6iZKKw0eMJbuMTIyoZ9940ecNlac6dqCpy3eiCq
   
   # To regenerate with a different key:
   ./generate-cloud-init.sh
   ```

3. **Create VPS with cloud-init:**
   - Paste the cloud-init.yaml content during VPS creation
   - Or upload as user-data file

#### Option B: Manual Setup (If cloud-init not supported)

```bash
# 1. Connect to your VPS
ssh root@your-server-ip

# 2. Download and run the setup
curl -fsSL https://raw.githubusercontent.com/yourusername/mapmap/main/cloud-init.yaml | \
  grep -A 1000 "runcmd:" | tail -n +2 | head -n -2 | bash
```

### 3. Post-Deployment Configuration

#### Update Configuration
```bash
# SSH to your server
ssh mapmap@your-server-ip

# Edit environment configuration
nano /home/mapmap/mapmap/.env
```

**Critical settings to update:**
```env
# Replace with your actual domain
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Generate a secure secret key
SECRET_KEY=your-secure-random-string-here
```

#### Setup SSL Certificate
```bash
# Run SSL setup script (replace with your domain and email)
sudo -u mapmap /home/mapmap/setup-ssl.sh yourdomain.com admin@yourdomain.com
```

#### Enable Auto-Start
```bash
# Enable MapMap service to start on boot
sudo systemctl enable mapmap
sudo systemctl start mapmap
```

### 4. DNS Configuration

Point your domain to the VPS:
```
Type    Name    Value           TTL
A       @       YOUR_VPS_IP     300
A       www     YOUR_VPS_IP     300
```

### 5. Verification

```bash
# Check service status
sudo -u mapmap /home/mapmap/monitor-mapmap.sh

# Test endpoints
curl https://yourdomain.com/health
curl https://yourdomain.com/tiles/10/500/400
```

## VPS Provider Specific Instructions

### DigitalOcean

1. Create Droplet → Ubuntu 22.04
2. Advanced Options → User Data → Paste cloud-init.yaml
3. Add SSH Key
4. Create Droplet

### Linode

1. Create Linode → Ubuntu 22.04
2. Advanced Options → User Data → Paste cloud-init.yaml
3. Add SSH Key
4. Create Linode

### Vultr

1. Deploy Instance → Ubuntu 22.04
2. Additional Features → User Data → Paste cloud-init.yaml
3. SSH Keys → Add Key
4. Deploy

### Hetzner Cloud

1. Create Server → Ubuntu 22.04
2. SSH Key → Add Key
3. User Data → Paste cloud-init.yaml
4. Create Server

### AWS EC2

1. Launch Instance → Ubuntu 22.04 AMI
2. Configure Instance → Advanced → User Data → Paste cloud-init.yaml
3. Add Security Group (ports 22, 80, 443)
4. Select Key Pair
5. Launch

### Google Cloud

```bash
gcloud compute instances create mapmap-server \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --metadata-from-file user-data=cloud-init.yaml \
  --tags=http-server,https-server
```

### Azure

```bash
az vm create \
  --resource-group myResourceGroup \
  --name mapmap-server \
  --image Ubuntu2204 \
  --custom-data cloud-init.yaml \
  --generate-ssh-keys
```

## Security Configuration

### Firewall Rules (Applied automatically)
- Port 22 (SSH) - Open
- Port 80 (HTTP) - Open (redirects to HTTPS)
- Port 443 (HTTPS) - Open
- All other ports - Closed

### Additional Security

1. **Change SSH Port (optional):**
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Change Port 22 to Port 2222
   sudo systemctl restart ssh
   sudo ufw allow 2222/tcp
   sudo ufw delete allow ssh
   ```

2. **Disable Password Authentication:**
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Set PasswordAuthentication no
   sudo systemctl restart ssh
   ```

3. **Setup Fail2Ban (Already installed):**
   ```bash
   sudo systemctl status fail2ban
   sudo fail2ban-client status sshd
   ```

## Monitoring & Maintenance

### Service Monitoring
```bash
# Check service status
sudo -u mapmap /home/mapmap/monitor-mapmap.sh

# View logs
cd /home/mapmap/mapmap
docker-compose -f docker-compose.production.yml logs -f
```

### Updates
```bash
# Deploy updates
sudo -u mapmap /home/mapmap/deploy-mapmap.sh
```

### Backup
```bash
# Backup configuration
tar -czf mapmap-backup-$(date +%Y%m%d).tar.gz \
  /home/mapmap/mapmap/.env \
  /home/mapmap/mapmap/ssl/ \
  /home/mapmap/mapmap/nginx.conf
```

### Performance Tuning

For high-traffic deployments:

1. **Scale containers:**
   ```yaml
   # In docker-compose.production.yml
   services:
     mapmap:
       deploy:
         replicas: 3
   ```

2. **Increase cache:**
   ```env
   CACHE_SIZE=50000
   CACHE_TTL=14400
   ```

3. **Add Redis caching:**
   ```bash
   # Uncomment Redis service in docker-compose.production.yml
   docker-compose -f docker-compose.production.yml up -d redis
   ```

## Troubleshooting

### Common Issues

1. **Service not starting:**
   ```bash
   # Check Docker status
   sudo systemctl status docker
   
   # Check logs
   sudo -u mapmap docker-compose -f /home/mapmap/mapmap/docker-compose.production.yml logs
   ```

2. **SSL certificate issues:**
   ```bash
   # Check certificate status
   sudo certbot certificates
   
   # Renew certificate
   sudo certbot renew
   ```

3. **High memory usage:**
   ```bash
   # Check resource usage
   docker stats
   
   # Reduce cache size in .env
   CACHE_SIZE=5000
   ```

4. **DNS not resolving:**
   ```bash
   # Check DNS propagation
   dig yourdomain.com
   nslookup yourdomain.com
   ```

### Support

- **Logs:** Check `/home/mapmap/mapmap/logs/`
- **Configuration:** `/home/mapmap/mapmap/.env`
- **SSL:** `/etc/letsencrypt/live/yourdomain.com/`
- **Documentation:** `/home/mapmap/mapmap/DEPLOYMENT.md`

## Cost Optimization

### Resource Usage
- **Light usage:** 1 vCPU, 1GB RAM (~$5-10/month)
- **Medium usage:** 2 vCPU, 2GB RAM (~$10-20/month)
- **High usage:** 4 vCPU, 4GB RAM (~$20-40/month)

### Provider Comparison
| Provider | 2 vCPU, 2GB RAM | SSL | Bandwidth |
|----------|------------------|-----|-----------|
| DigitalOcean | $12/month | Free | 2TB |
| Linode | $12/month | Free | 2TB |
| Vultr | $12/month | Free | 2TB |
| Hetzner | €4.15/month | Free | 20TB |
| AWS EC2 | ~$15/month | Free | Pay-per-use |

## Scaling

For multiple regions or high availability:

1. **Multi-region deployment:**
   - Deploy to multiple VPS in different regions
   - Use GeoDNS to route traffic to nearest server

2. **Load balancer:**
   - Add Cloudflare or AWS CloudFront
   - Configure multiple origin servers

3. **Database backend:**
   - Add Redis cluster for distributed caching
   - Use external monitoring service