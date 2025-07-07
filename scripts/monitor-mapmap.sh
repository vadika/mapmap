#!/bin/bash

echo "📊 MapMap Service Status"
echo "======================="

cd /home/mapmap/mapmap

# Docker containers status
echo "🐳 Container Status:"
docker-compose -f docker-compose.production.yml ps

echo ""
echo "🔍 Health Check:"
curl -s http://localhost:8000/health | jq . || echo "❌ Health check failed"

echo ""
echo "📈 Metrics (if enabled):"
curl -s http://localhost:8000/metrics | grep -E "mapmap_.*_total" || echo "Metrics not available"

echo ""
echo "💾 System Resources:"
echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
echo "Load: $(uptime | cut -d',' -f3-)"

echo ""
echo "📝 Recent Logs:"
docker-compose -f docker-compose.production.yml logs --tail=20 mapmap