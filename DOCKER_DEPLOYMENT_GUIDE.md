# Docker & GitHub Deployment Guide

## Overview

Your AI agent is now containerized and ready for deployment with:
- ✅ Docker container setup
- ✅ Docker Compose orchestration
- ✅ GitHub Actions CI/CD pipelines
- ✅ Automated testing and security scanning
- ✅ Production deployment workflow

---

## 📦 Docker Setup

### Dockerfile
- **Base Image**: Python 3.11-slim (lightweight)
- **Working Directory**: `/app`
- **Security**: Runs as non-root user (appuser)
- **Health Check**: Included
- **Resource Limits**: Configurable

### docker-compose.yml
Includes 3 services:
1. **ai-agent** - Main application
2. **ollama** - Local LLM inference
3. **qdrant** - Vector database (optional)

---

## 🚀 Quick Start

### 1. Build Locally
```bash
docker-compose build
```

### 2. Run Locally
```bash
docker-compose up -d
```

### 3. View Logs
```bash
docker-compose logs -f ai-agent
```

### 4. Stop Services
```bash
docker-compose down
```

### 5. Clean Up
```bash
docker-compose down -v  # Remove volumes too
```

---

## 🔧 Configuration

### Create `.env` file
```bash
# API Keys
GOOGLE_API_KEY=your-key-here
GROQ_API_KEY=your-key-here

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Optional
QDRANT_API_KEY=admin
OLLAMA_HOST=http://ollama:11434
```

### Environment Variables
```
PYTHONUNBUFFERED=1          # Real-time logs
PYTHONDONTWRITEBYTECODE=1   # Skip .pyc files
APP_ENV=production          # Environment
LOG_LEVEL=INFO             # Logging level
```

---

## GitHub Actions Workflows

### 1. **docker-build.yml** - Build & Push
**Triggers**: Push to main/develop, PRs, manual trigger

**Jobs**:
- Build Docker image
- Push to GitHub Container Registry (GHCR)
- Security scanning with Trivy
- Cache for faster builds

**Tags**:
- `main` → `latest`
- Tags → `v1.0.0`
- PRs → `pr-123`
- Commits → `sha-abc123`

### 2. **deploy.yml** - Deploy to Production
**Triggers**: Push to main, version tags

**Jobs**:
- Pull latest image from GHCR
- Deploy via SSH to server
- Run health checks
- Notify Slack on success/failure

**Requirements**:
- SSH access to server
- Slack webhook (optional)

### 3. **tests.yml** - Tests & Code Quality
**Triggers**: Push/PR to main/develop

**Jobs**:
- Run pytest (Python 3.11, 3.12)
- Lint with flake8, black, isort
- Security scan with bandit
- Type check with mypy
- Docker image test

---

## 📋 Setup Steps

### Step 1: Enable GitHub Container Registry
```bash
# GitHub Container Registry is enabled by default
# Just authenticate locally:
docker login ghcr.io -u <username> -p <github-token>
```

### Step 2: Set GitHub Secrets
Go to: Settings → Secrets and variables → Actions

Required secrets:
```
DEPLOYER_HOST           # Your server IP/domain
DEPLOYER_USER           # SSH username
DEPLOYER_SSH_KEY        # SSH private key
SLACK_WEBHOOK_URL       # (Optional) Slack webhook
AWS_ACCESS_KEY_ID       # (Optional) AWS credentials
AWS_SECRET_ACCESS_KEY   # (Optional) AWS credentials
AWS_REGION              # (Optional) AWS region
```

### Step 3: Configure SSH Keys
```bash
# Generate SSH key
ssh-keygen -t rsa -b 4096 -f deploy_key

# Add public key to server
cat deploy_key.pub | ssh user@server "cat >> ~/.ssh/authorized_keys"

# Add private key to GitHub Secrets
cat deploy_key | base64
# Copy output to DEPLOYER_SSH_KEY secret
```

### Step 4: Update Deployed Server
Ensure deployed server has:
```bash
# Docker & Docker Compose installed
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p /app
cd /app

# Create docker-compose.yml and .env on server
```

---

## 🔐 Security Features

### 1. Container Security
- ✅ Non-root user (appuser)
- ✅ Minimal base image (python:3.11-slim)
- ✅ No unnecessary packages
- ✅ Health checks included

### 2. Secrets Management
- ✅ Sensitive data in GitHub Secrets
- ✅ Not committed to repository
- ✅ Environment variables injected at runtime

### 3. Image Scanning
- ✅ Trivy vulnerability scanner
- ✅ Runs on every build
- ✅ Results uploaded to GitHub Security
- ✅ Fails build if critical vulnerabilities found

### 4. Code Quality
- ✅ Linting (flake8)
- ✅ Type checking (mypy)
- ✅ Security scanning (bandit)
- ✅ Dependency checking (safety)

---

## 📊 Monitoring & Logs

### View Container Logs
```bash
docker-compose logs -f ai-agent
docker-compose logs -f ollama
docker-compose logs -f qdrant
```

### Check Container Health
```bash
docker-compose ps
```

### SSH into Container
```bash
docker-compose exec -it ai-agent /bin/bash
```

### View Resource Usage
```bash
docker stats
```

---

## 🔄 CI/CD Pipeline Overview

```
┌─────────────────┐
│  Push to GitHub │
└────────┬────────┘
         │
         ├─→ Tests Workflow
         │   ├─ Pytest
         │   ├─ Linting
         │   ├─ Security scan
         │   └─ Docker test
         │
         ├─→ Docker Build Workflow
         │   ├─ Build image
         │   ├─ Push to GHCR
         │   ├─ Security scan
         │   └─ Cache
         │
         └─→ Deploy Workflow (if main/tags)
             ├─ Pull latest image
             ├─ SSH deploy
             ├─ Health check
             └─ Slack notify
```

---

## 📝 Docker Tags & Versions

### Default Tags
- `latest` - Latest build on main branch
- `main` - Current main branch build
- `develop` - Current develop branch build
- `v1.0.0` - Release version tagged in git

### Example Push & Usage
```bash
# Build and push
docker-compose build
docker push ghcr.io/your-org/generativeai-agent:latest

# Pull and run
docker pull ghcr.io/your-org/generativeai-agent:latest
docker run -it ghcr.io/your-org/generativeai-agent:latest
```

---

## 🐛 Troubleshooting

### Issue: Image won't build
```bash
# Check Docker daemon
docker --version
docker ps

# Clean cache
docker system prune -a
docker-compose build --no-cache
```

### Issue: Container crashes
```bash
# Check logs
docker-compose logs ai-agent

# Verify configuration
docker inspect <container-id>

# Check resource usage
docker stats
```

### Issue: Network issues
```bash
# Test network
docker-compose exec ai-agent ping ollama

# Check DNS
docker-compose exec ai-agent nslookup ollama

# Inspect network
docker network inspect ai-network
```

### Issue: GitHub Actions fail
```bash
# Check workflow logs
# Go to: Actions → Workflow → Run

# Check for missing secrets
# Settings → Secrets → Verify all required secrets
```

---

## 📚 Files Created

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Service orchestration |
| `.dockerignore` | Files to exclude from build |
| `.github/workflows/docker-build.yml` | Build & push workflow |
| `.github/workflows/deploy.yml` | Production deployment |
| `.github/workflows/tests.yml` | Testing & linting |

---

## 🎯 Next Steps

1. ✅ Create `.env` file with your keys
2. ✅ Add GitHub Secrets (DEPLOYER_HOST, etc.)
3. ✅ Set up SSH access to server
4. ✅ Push to GitHub
5. ✅ Monitor GitHub Actions
6. ✅ Deploy to production

---

## 💡 Best Practices

### Development
```bash
# Build locally
docker-compose build

# Test locally
docker-compose up
docker-compose logs -f

# Clean up
docker-compose down -v
```

### Production
```bash
# Monitor logs
docker-compose logs -f ai-agent

# Scale services (if needed)
docker-compose up -d --scale ai-agent=3

# Update versions
docker pull ghcr.io/your-org/generativeai-agent:latest
docker-compose up -d
```

### Security
- Never commit `.env` file
- Rotate SSH keys regularly
- Use strong API keys
- Monitor image vulnerabilities
- Keep base images updated

---

## 📞 Resources

- **Docker Docs**: https://docs.docker.com
- **GitHub Actions**: https://docs.github.com/en/actions
- **Container Registry**: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- **Ollama**: https://ollama.ai
- **Qdrant**: https://qdrant.tech

---

*Docker & GitHub Deployment Setup Complete - 2026-02-19*
