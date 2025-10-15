# Docker Deployment Guide

Complete guide for deploying Smart Support Operator Interface using Docker.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose v2.0+
- At least 4GB RAM available for containers
- Scibox API key

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/pandarun/smart-support.git
   cd smart-support
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your SCIBOX_API_KEY
   ```

3. **Build and start services**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Architecture

The deployment consists of two services:

### Backend Service
- **Image**: `smart-support-backend:latest`
- **Port**: 8000
- **Technology**: Python 3.12, FastAPI, Uvicorn
- **Includes**:
  - Classification Module (LLM-powered inquiry classification)
  - Retrieval Module (semantic search with embeddings)
  - REST API endpoints
  - Persistent SQLite storage for embeddings

### Frontend Service
- **Image**: `smart-support-frontend:latest`
- **Port**: 3000 (mapped to container port 80)
- **Technology**: React 18, TypeScript, Vite, Tailwind CSS
- **Server**: Nginx with optimized configuration

## Environment Variables

### Required
- `SCIBOX_API_KEY`: Your Scibox LLM API key (required for classification)

### Optional
- `API_TIMEOUT`: API request timeout in seconds (default: 20)
- `API_MAX_RETRIES`: Maximum retry attempts for API calls (default: 3)
- `STORAGE_BACKEND`: Storage backend type (default: sqlite)
- `DATABASE_URL`: Database connection string (default: sqlite:///data/embeddings.db)

### Example .env file
```bash
SCIBOX_API_KEY=sk-your-api-key-here
API_TIMEOUT=20
API_MAX_RETRIES=3
STORAGE_BACKEND=sqlite
```

## Docker Commands

### Build images
```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend
docker-compose build frontend

# Build without cache (clean build)
docker-compose build --no-cache
```

### Start services
```bash
# Start in foreground (see logs)
docker-compose up

# Start in background (detached)
docker-compose up -d

# Start and rebuild if needed
docker-compose up --build
```

### Stop services
```bash
# Stop containers (keeps data)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers, and delete volumes
docker-compose down -v
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100
```

### Check status
```bash
# List running containers
docker-compose ps

# Check health
docker-compose ps
curl http://localhost:8000/health
```

## Volume Management

### Persistent Data
The deployment uses a named volume to persist embeddings data:
- `embeddings-data`: Stores pre-computed embeddings from FAQ database

### Backup embeddings
```bash
# Create backup
docker run --rm -v smart-support_embeddings-data:/data -v $(pwd):/backup alpine tar czf /backup/embeddings-backup.tar.gz /data

# Restore backup
docker run --rm -v smart-support_embeddings-data:/data -v $(pwd):/backup alpine tar xzf /backup/embeddings-backup.tar.gz -C /
```

## Resource Limits

### Backend
- CPU: 0.5-2.0 cores
- Memory: 512MB-2GB
- Storage: ~100MB (embeddings database)

### Frontend
- CPU: 0.25-1.0 cores
- Memory: 128MB-512MB
- Storage: ~50MB (static assets)

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Missing SCIBOX_API_KEY: Add to .env file
# - Port 8000 in use: Stop other services or change port mapping
# - Out of memory: Increase Docker Desktop memory limit
```

### Frontend can't connect to backend
```bash
# Verify backend is healthy
curl http://localhost:8000/health

# Check nginx logs
docker-compose logs frontend

# Verify network connectivity
docker-compose exec frontend ping backend
```

### Embeddings not loading
```bash
# Check data volume
docker volume inspect smart-support_embeddings-data

# Restart backend to regenerate
docker-compose restart backend
docker-compose logs -f backend
# Wait for "Loaded X embeddings in Ys" message
```

### Slow classification requests
- Increase `API_TIMEOUT` in .env (default: 20s)
- Check Scibox API status
- Monitor backend logs for retry attempts

### Docker daemon issues
```bash
# Restart Docker Desktop
# On macOS:
osascript -e 'quit app "Docker"' && open -a Docker

# Clear build cache
docker builder prune -af

# Reset Docker Desktop (nuclear option)
# Docker Desktop > Troubleshoot > Reset to factory defaults
```

## Production Deployment

### Recommendations
1. **Use PostgreSQL for storage** (better than SQLite for production)
   - Uncomment PostgreSQL service in docker-compose.yml
   - Set `STORAGE_BACKEND=postgres` in .env

2. **Enable HTTPS**
   - Add nginx SSL configuration
   - Use Let's Encrypt for certificates

3. **Set resource limits**
   - Adjust deploy.resources in docker-compose.yml
   - Monitor with `docker stats`

4. **Health monitoring**
   - Set up monitoring for `/health` endpoint
   - Configure alerting for service failures

5. **Backup strategy**
   - Regular backups of embeddings volume
   - Database backups if using PostgreSQL

### Security
- Never commit .env file with real API keys
- Use Docker secrets for sensitive data in production
- Enable firewall rules to limit access
- Regular security updates for base images

## Performance Optimization

### Backend
- Pre-compute embeddings on container startup (already done)
- Use connection pooling for database
- Enable response caching for frequent queries

### Frontend
- Nginx gzip compression enabled by default
- Static assets cached for 1 year
- Minified production build

## Scaling

### Horizontal Scaling
```yaml
# In docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3  # Run 3 backend instances
```

### Load Balancing
- Add nginx reverse proxy in front
- Use Docker Swarm or Kubernetes for orchestration

## Testing Deployment

```bash
# 1. Start services
docker-compose up -d

# 2. Wait for services to be healthy
docker-compose ps

# 3. Test backend health
curl http://localhost:8000/health

# 4. Test classification endpoint
curl -X POST http://localhost:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"inquiry": "Как открыть счет в банке?"}'

# 5. Open frontend in browser
open http://localhost:3000
```

## Cleanup

```bash
# Stop and remove everything
docker-compose down -v

# Remove images
docker rmi smart-support-backend:latest
docker rmi smart-support-frontend:latest

# Clean up build cache
docker builder prune -af
```

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- View API docs: http://localhost:8000/docs
- GitHub Issues: https://github.com/pandarun/smart-support/issues
