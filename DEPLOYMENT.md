# MapMap Production Deployment Guide

## Overview

This guide covers deploying MapMap tile proxy to production with proper security, monitoring, and scalability considerations.

## Quick Start

### 1. Environment Setup

```bash
# Copy production environment template
cp .env.production .env

# Edit configuration
nano .env
```

Key settings to configure:
- `ALLOWED_ORIGINS`: Your domain(s)
- `ALLOWED_HOSTS`: Your domain(s) 
- `SECRET_KEY`: Generate a secure key
- `LOG_LEVEL`: Set to WARNING for production

### 2. Production Deployment

```bash
# Build and start production services
docker-compose -f docker-compose.production.yml up -d

# Check health
curl http://localhost:8000/health
```

## Architecture

```
[Client] → [Nginx] → [MapMap] → [WMTS Server]
                   ↓
                [Redis Cache] (optional)
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LOG_LEVEL` | Logging level | WARNING | No |
| `CACHE_SIZE` | In-memory cache size | 10000 | No |
| `CACHE_TTL` | Cache TTL in seconds | 7200 | No |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | * | Yes |
| `ALLOWED_HOSTS` | Trusted hosts (comma-separated) | * | Yes |
| `SECRET_KEY` | Application secret | None | Yes |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | false | No |
| `RATE_LIMIT_REQUESTS` | Requests per hour | 1000 | No |
| `ENABLE_METRICS` | Enable Prometheus metrics | false | No |

### Production Security

1. **CORS Configuration**
   ```env
   ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

2. **Host Validation**
   ```env
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```

3. **Rate Limiting**
   ```env
   RATE_LIMIT_ENABLED=true
   RATE_LIMIT_REQUESTS=1000
   RATE_LIMIT_WINDOW=3600
   ```

## SSL/TLS Setup

### Option 1: Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Option 2: Custom Certificates

1. Place certificates in `./ssl/` directory:
   - `cert.pem` - Certificate chain
   - `key.pem` - Private key

2. Uncomment HTTPS server block in `nginx.conf`

3. Update `docker-compose.production.yml` to mount SSL directory

## Monitoring

### Health Checks

- **Liveness**: `GET /health` - Basic health status
- **Readiness**: `GET /ready` - Service ready for traffic
- **Metrics**: `GET /metrics` - Prometheus metrics (if enabled)

### Prometheus Metrics

Enable metrics collection:
```env
ENABLE_METRICS=true
```

Available metrics:
- `mapmap_requests_total` - Total requests by endpoint/method/status
- `mapmap_request_duration_seconds` - Request duration histogram
- `mapmap_cache_hits_total` - Cache hit counter
- `mapmap_cache_misses_total` - Cache miss counter

### Log Aggregation

Logs are written to stdout/stderr and can be collected by:
- Docker logging drivers
- ELK Stack
- Fluentd
- CloudWatch Logs

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.production.yml
services:
  mapmap:
    deploy:
      replicas: 3
```

### Load Balancing

Nginx is configured for load balancing:
- Health checks on `/health`
- Upstream keepalive connections
- Proper error handling

### Caching Strategy

1. **Application Cache**: In-memory TTL cache (per instance)
2. **Nginx Cache**: HTTP caching for tiles (shared)
3. **Redis Cache**: Optional distributed cache (future enhancement)

## Performance Tuning

### Docker Resources

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

### Nginx Optimization

- Gzip compression enabled
- Keepalive connections
- Rate limiting by endpoint type
- Optimized timeouts

### Application Optimization

- Gunicorn with multiple workers
- Async HTTP client with connection pooling
- Efficient coordinate transformations
- Optimized caching strategy

## Deployment Strategies

### Blue-Green Deployment

```bash
# Deploy new version
docker-compose -f docker-compose.production.yml up -d --scale mapmap=2

# Health check new instances
curl http://localhost:8000/health

# Switch traffic (update nginx upstream)
# Stop old instances
```

### Rolling Updates

```bash
# Update image
docker-compose -f docker-compose.production.yml pull

# Rolling restart
docker-compose -f docker-compose.production.yml up -d --no-deps mapmap
```

## Security Checklist

- [ ] HTTPS configured with valid certificates
- [ ] CORS properly configured for your domains
- [ ] Rate limiting enabled
- [ ] Security headers configured in Nginx
- [ ] Non-root user in Docker containers
- [ ] Secrets managed securely (not in code)
- [ ] Regular security updates applied
- [ ] Network access restricted (firewall rules)
- [ ] Monitoring and alerting configured
- [ ] Backup and disaster recovery plan

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Check `ALLOWED_ORIGINS` configuration
   - Verify domain spelling and protocol (http/https)

2. **Rate Limiting**
   - Check Nginx error logs
   - Adjust rate limits in nginx.conf
   - Monitor `/metrics` for rate limit hits

3. **High Memory Usage**
   - Reduce `CACHE_SIZE`
   - Monitor cache hit ratios
   - Consider Redis for distributed caching

4. **Slow Responses**
   - Check WMTS server performance
   - Monitor request duration metrics
   - Increase cache TTL for stable data

### Log Analysis

```bash
# Application logs
docker-compose -f docker-compose.production.yml logs mapmap

# Nginx logs
docker-compose -f docker-compose.production.yml logs nginx

# Follow logs in real-time
docker-compose -f docker-compose.production.yml logs -f
```

### Performance Monitoring

```bash
# Resource usage
docker stats

# Request metrics (if enabled)
curl http://localhost:8000/metrics | grep mapmap_

# Cache statistics
curl http://localhost:8000/health | jq .cache_size
```

## Maintenance

### Regular Tasks

1. **Log Rotation**: Configure with logrotate or Docker logging
2. **Certificate Renewal**: Automated with certbot
3. **Security Updates**: Regular Docker image updates
4. **Cache Cleanup**: Automatic with TTL
5. **Monitoring**: Regular health check monitoring

### Backup Strategy

- Configuration files (environment, nginx.conf)
- SSL certificates
- Custom coordinate system configurations
- Monitoring/alerting configurations

### Updates

```bash
# Pull latest images
docker-compose -f docker-compose.production.yml pull

# Restart with new images
docker-compose -f docker-compose.production.yml up -d

# Verify deployment
curl http://localhost:8000/health
```

## Support

For issues and questions:
1. Check application logs
2. Verify configuration
3. Check WMTS server availability
4. Review this deployment guide
5. Check project repository for updates