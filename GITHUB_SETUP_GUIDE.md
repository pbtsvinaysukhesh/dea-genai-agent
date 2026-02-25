# GitHub CI/CD Setup Guide

## Complete Setup Instructions

### Step 1: Prepare Your Environment

#### 1.1 Create `.env` file (DO NOT COMMIT)
```bash
cat > .env << 'EOF'
# API Authentication
GOOGLE_API_KEY=your-google-api-key
GROQ_API_KEY=your-groq-api-key

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Optional Services
QDRANT_API_KEY=admin
OLLAMA_HOST=http://ollama:11434

# Application
APP_ENV=production
LOG_LEVEL=INFO
EOF

# Add to .gitignore
echo ".env" >> .gitignore
```

#### 1.2 Add .gitignore entry
```bash
# Make sure .env is in .gitignore
echo ".env*" >> .gitignore
```

---

### Step 2: GitHub Secrets Configuration

Go to: **Settings** → **Secrets and variables** → **Actions**

Click **New repository secret** and add:

#### Required Secrets (for deployment)
```
Name: DEPLOYER_HOST
Value: your.server.com or 192.168.1.100

Name: DEPLOYER_USER
Value: ubuntu  (or your SSH user)

Name: DEPLOYER_SSH_KEY
Value: (your SSH private key in base64)

Name: SLACK_WEBHOOK_URL
Value: https://hooks.slack.com/services/... (optional)
```

#### AWS Secrets (optional, for AWS deployment)
```
Name: AWS_ACCESS_KEY_ID
Value: AKIAIOSFODNN7EXAMPLE

Name: AWS_SECRET_ACCESS_KEY
Value: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

Name: AWS_REGION
Value: us-east-1
```

---

### Step 3: SSH Key Setup

#### 3.1 Generate SSH key locally
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/deploy_key -N ""

# If on Windows Git Bash:
ssh-keygen -t rsa -b 4096 -f deploy_key -N ""
```

#### 3.2 Add public key to server
```bash
# On your local machine:
cat ~/.ssh/deploy_key.pub

# SSH into server and add:
mkdir -p ~/.ssh
cat >> ~/.ssh/authorized_keys << 'EOF'
ssh-rsa AAAA... (paste the public key content)
EOF

chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

#### 3.3 Convert private key to base64
```bash
# On Linux/Mac:
cat ~/.ssh/deploy_key | base64 | tr -d '\n'

# On Windows Git Bash:
cat deploy_key | base64 | tr -d '\n'
```
**Copy the output and paste as DEPLOYER_SSH_KEY secret**

---

### Step 4: Server Setup

#### 4.1 Install Docker & Docker Compose
```bash
# SSH into server
ssh user@your.server.com

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version
```

#### 4.2 Create app directory
```bash
mkdir -p /app
cd /app

# Create directories
mkdir -p data/knowledge logs results/daily models config

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
# Copy content from docker-compose.yml in your repo
EOF

# Create .env (from template)
nano .env  # Edit with your actual keys
chmod 600 .env
```

#### 4.3 Configure git for auto-pull (optional)
```bash
cd /app
git init
git remote add origin https://github.com/your-org/your-repo.git
git pull origin main
```

---

### Step 5: GitHub Workflow Configuration

#### 5.1 Create workflow secrets environment
The workflows will use these secrets:
- `DEPLOYER_HOST` - Server to deploy to
- `DEPLOYER_USER` - SSH user
- `DEPLOYER_SSH_KEY` - SSH private key

#### 5.2 Configure workflow permissions
Go to: **Settings** → **Actions** → **General**

Configure:
- ✅ Allow GitHub Actions to create and approve pull requests
- ✅ Workflow permissions: Read and write permissions

---

### Step 6: Test Your Setup

#### 6.1 Trigger tests workflow
```bash
# Push to GitHub
git add .
git commit -m "Add Docker & CI/CD setup"
git push origin main

# Navigate to your repo
# Click "Actions" tab
# You should see "Tests & Code Quality" workflow running
```

#### 6.2 Verify workflow runs
```bash
# Wait for workflow to complete
# Check for:
- ✅ Tests pass
- ✅ Linting passes (or warnings)
- ✅ Docker image builds
```

#### 6.3 Test deployment (manual)
```bash
# In GitHub Actions tab
# Find "Deploy to Production" workflow
# Click "Run workflow" → "Run workflow"
# Select environment: staging or production
```

---

### Step 7: Configure Slack Notifications (Optional)

#### 7.1 Create Slack App
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "github-deployer", Workspace: select yours
4. Click "Incoming Webhooks" → "Add New Webhook to Workspace"
5. Select channel: #deployments
6. Copy Webhook URL

#### 7.2 Add Slack webhook to secrets
In GitHub Secrets, add:
```
Name: SLACK_WEBHOOK_URL
Value: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
```

---

## 📊 Workflow Triggers

### docker-build.yml
**Automatically runs on**:
- Push to `main` branch
- Push to `develop` branch
- Any git tag (v1.0.0, etc.)
- Manual trigger (Actions tab)
- Pull requests to main/develop

**Manual trigger**:
```
Go to Actions → Docker Build & Push → Run workflow
```

### deploy.yml
**Automatically runs on**:
- Push to `main` branch
- Git tags (v1.0.0, etc.)
- Manual trigger (Actions tab)
- After docker-build succeeds

**Manual trigger**:
```
Actions → Deploy to Production → Run workflow → Select environment
```

### tests.yml
**Automatically runs on**:
- Push to `main` or `develop`
- Pull requests to main/develop
- Manual trigger

---

## 🔍 Monitoring Workflows

### View Workflow Status
1. Click **Actions** tab in GitHub repo
2. Select workflow name (docker-build, deploy, tests)
3. Click run to view detailed logs

### Workflow Artifacts
After tests run:
1. Click on workflow run
2. Scroll to "Artifacts" section
3. Download:
   - `coverage-report-*` - Test coverage
   - `security-reports` - Security scan results

### Real-time Logs
```bash
# On server, watch deployment
ssh user@your.server.com
cd /app
docker-compose logs -f ai-agent

# In another terminal, watch previous deployments
docker ps -a
```

---

## 🚀 Deployment Process

### Automatic Deployment
```
1. Developer pushes to main
   ↓
2. GitHub Actions triggers tests.yml
   ├─ Run pytest
   ├─ Linting
   ├─ Security scan
   └─ Build Docker image
   ↓
3. If all tests pass, triggers docker-build.yml
   ├─ Build Docker image
   ├─ Push to GHCR
   ├─ Security scan
   └─ Cache layers
   ↓
4. If docker build succeeds, triggers deploy.yml
   ├─ SSH to server
   ├─ Pull latest image
   ├─ Run docker-compose up
   ├─ Health check
   └─ Slack notification
```

### Manual Deployment
```
1. Go to GitHub Actions
2. Select "Deploy to Production"
3. Click "Run workflow"
4. Choose environment (staging/production)
5. Workflow executes manually
```

---

## 📈 Monitoring & Troubleshooting

### Check Workflow Failures
1. Click Actions → Failed workflow
2. Click job to see error details
3. Common errors:
   - Missing secrets → Add to GitHub Secrets
   - SSH key issues → Verify key format
   - Deployment server down → Check server status

### Fix Common Issues

**Issue: "Authentication failed"**
```bash
# Generate new SSH key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/deploy_key
# Update in GitHub Secrets
```

**Issue: "Docker pull failed"**
```bash
# Check Docker login on server
docker login ghcr.io
# Or use Personal Access Token
docker login ghcr.io -u <username> -p <PAT>
```

**Issue: "Connection refused"**
```bash
# Check server is reachable
ping your.server.com
ssh user@your.server.com

# Check docker-compose is installed
docker-compose --version
```

**Issue: "Insufficient disk space"**
```bash
# SSH to server
docker system prune -a
docker volume prune
rm -rf data/knowledge/* # If safe
```

---

## 📋 Checklist

### Setup Checklist
- [ ] Created `.env` file (not committed)
- [ ] Added `.env` to `.gitignore`
- [ ] Generated SSH key pair
- [ ] Added public key to server
- [ ] Installed Docker on server
- [ ] Set up GitHub Secrets (6 required)
- [ ] Created app directory on server
- [ ] Verified SSH access from local machine
- [ ] Tested locally with `docker-compose up`

### Before First Deployment
- [ ] All GitHub Secrets configured
- [ ] SSH keys working (test: `ssh user@server`)
- [ ] Server can reach GitHub (test: `git clone`)
- [ ] Docker running on server
- [ ] Firewall allows SSH (port 22)
- [ ] `.env` file on server with correct values

### After First Deployment
- [ ] Service is running (`docker-compose ps`)
- [ ] Health check passes (`curl http://server:8000/health`)
- [ ] Ollama is loaded (`curl http://server:11434/api/tags`)
- [ ] API responds (`curl http://server:8000/api/papers`)
- [ ] Logs are clean (`docker-compose logs ai-agent`)

---

## 🔐 Security Best Practices

1. **Never commit secrets**
   ```bash
   # Check before pushing
   git diff HEAD
   grep -r "GOOGLE_API_KEY" .
   ```

2. **Rotate SSH keys regularly**
   ```bash
   # Monthly rotation
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/deploy_key_new
   # Update on server and in GitHub Secrets
   ```

3. **Monitor GitHub Actions logs**
   - Check for exposed secrets
   - Review deployment logs
   - Watch for suspicious activity

4. **Use ephemeral keys for CI/CD**
   - Consider using time-limited tokens
   - Rotate regularly

---

## 📞 Quick Reference

### Common Commands

**Local Testing**
```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
docker-compose down -v
```

**Server Deployment (Manual)**
```bash
ssh user@server.com
cd /app
docker pull ghcr.io/org/repo:latest
docker-compose up -d
docker-compose ps
```

**View GitHub Actions**
```bash
# Web: https://github.com/your-org/your-repo/actions
# Or use GitHub CLI:
gh run list
gh run view <run-id>
```

---

*GitHub CI/CD Setup Complete - 2026-02-19*
