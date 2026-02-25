# GitHub Upload & Hosting Guide

## Step 1: Create GitHub Repository

### Option A: Create via GitHub Web Interface (Recommended)

1. Go to https://github.com/new
2. **Repository name:** `GenerativeAI-agent` (or your preferred name)
3. **Description:** "On-Device AI Memory Intelligence Agent with Multi-Format Reports"
4. **Visibility:** Private or Public (choose based on preference)
5. **Initialize repository:** Leave unchecked (we already have commits)
6. Click **Create repository**

### Option B: Create via GitHub CLI

```bash
# Install GitHub CLI if needed: https://cli.github.com

gh repo create GenerativeAI-agent \
  --source=. \
  --remote=origin \
  --push \
  --private
```

---

## Step 2: Add Remote & Push Code

### Using HTTPS (Simpler, recommended for first time)

```bash
# Navigate to your project
cd /c/Users/PBTSVS/Desktop/GenerativeAI-agent

# Add remote (replace USERNAME with your GitHub username)
git remote add origin https://github.com/USERNAME/GenerativeAI-agent.git

# Rename branch to main if needed
git branch -M main

# Push code
git push -u origin main
```

**When prompted for password:**
- Username: Your GitHub username
- Password: Use a Personal Access Token (not your password)
  - Create token: https://github.com/settings/tokens/new
  - Scopes needed: `repo`, `workflow`

### Using SSH (More secure, requires setup)

```bash
# Add remote
git remote add origin git@github.com:USERNAME/GenerativeAI-agent.git

# Push code
git push -u origin main
```

**First time SSH setup:**
```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your-email@example.com"

# Add to SSH agent (Windows Git Bash)
eval `ssh-agent -s`
ssh-add ~/.ssh/id_ed25519

# Add public key to GitHub
# Copy: cat ~/.ssh/id_ed25519.pub
# Go to: https://github.com/settings/keys
# Click "New SSH key" and paste
```

---

## Step 3: Verify Upload

```bash
# Check remote is configured
git remote -v

# Check branch is pushed
git log --oneline | head -5
```

Expected output:
```
origin  https://github.com/USERNAME/GenerativeAI-agent.git (fetch)
origin  https://github.com/USERNAME/GenerativeAI-agent.git (push)
```

---

## Step 4: Hosting Options

Choose one based on your needs:

### Option 1: GitHub Pages (For Dashboard/Frontend)

✅ **Good for:** Web dashboard, documentation
❌ **Not for:** Python backend (requires serverless)

**Setup:**
1. Go to repository Settings → Pages
2. Source: Deploy from a branch
3. Branch: gh-pages
4. Folder: /docs or /Dashboard/frontend

**Deploy with GitHub Actions:**
```yaml
# Create .github/workflows/pages.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Upload to Pages
        uses: actions/upload-pages-artifact@v1
        with:
          path: 'Dashboard/frontend'
      - name: Deploy
        uses: actions/deploy-pages@v1
```

---

### Option 2: Docker + GitHub Container Registry (Recommended)

✅ **Good for:** Full application, already have Dockerfile
✅ **Can be deployed anywhere** (Railway, Render, etc.)

**Setup Docker image:**

```yaml
# Create .github/workflows/docker-push.yml
name: Build & Push Docker Image

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

**Then deploy Docker image to:**
- ✅ Railway: https://railway.app (recommended)
- ✅ Render: https://render.com
- ✅ Fly.io: https://fly.io
- ✅ Vercel (with serverless)
- ✅ AWS ECS
- ✅ Google Cloud Run
- ✅ Azure Container Instances

---

### Option 3: Railway.app (Easiest for Python)

✅ **Good for:** Simple deployment, automatic scaling
✅ **Free tier available**

**Steps:**

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Configure environment variables:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```
6. Railway auto-deploys on push!

---

### Option 4: Render.com (Also Simple)

✅ **Good for:** Python applications
✅ **Free tier available**

1. Go to https://render.com
2. Connect GitHub
3. Select repository
4. Create Web Service
5. Runtime: Docker
6. Select Dockerfile
7. Set environment variables
8. Deploy!

---

### Option 5: GitHub Actions + Scheduled Runs

✅ **Good for:** Scheduled daily/weekly reports
❌ **Not for:** Always-on service

**Setup scheduled execution:**

```yaml
# Create .github/workflows/scheduled-pipeline.yml
name: Scheduled AI Pipeline

on:
  schedule:
    # Runs every day at 9 AM UTC
    - cron: '0 9 * * *'
  workflow_dispatch:  # Manual trigger

jobs:
  run-pipeline:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run pipeline
        env:
          SMTP_SERVER: ${{ secrets.SMTP_SERVER }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
        run: |
          python main.py

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: pipeline-results
          path: results/
          retention-days: 30
```

---

## Recommended Setup: Railway + Docker

Here's the optimal deployment for your use case:

### Step-by-Step:

**1. Create GitHub repo (done above)**

**2. Add Docker push workflow:**
```bash
# Create .github/workflows/docker-push.yml (see Option 2 above)
```

**3. Deploy to Railway:**

1. Visit https://railway.app
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your `GenerativeAI-agent` repository
5. Railway will auto-detect Dockerfile
6. Add environment variables (Settings):
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email
   SMTP_PASSWORD=your-app-password
   ```
7. Click "Deploy" → Done!

**4. Setup scheduled runs:**
- Add `.github/workflows/scheduled-pipeline.yml` (see Option 5)
- Railway will execute on schedule

---

## Quick Command Summary

```bash
# 1. Add remote
git remote add origin https://github.com/YOUR_USERNAME/GenerativeAI-agent.git

# 2. Verify remote
git remote -v

# 3. Create/verify main branch
git branch -M main

# 4. Push code
git push -u origin main

# 5. Verify on GitHub
# Go to: https://github.com/YOUR_USERNAME/GenerativeAI-agent
```

---

## GitHub Secrets Setup (For Automated Deployments)

1. Go to: Repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret:

```
SMTP_SERVER = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = your-email@example.com
SMTP_PASSWORD = your-app-specific-password
DOCKER_HUB_USERNAME = your-username (optional)
DOCKER_HUB_TOKEN = your-token (optional)
```

---

## File Structure for GitHub

```
GenerativeAI-agent/
├── .github/
│   └── workflows/           # GitHub Actions
│       ├── docker-push.yml
│       ├── scheduled-pipeline.yml
│       └── tests.yml
├── src/                      # Python source
├── Dashboard/                # Web frontend
├── config/                   # Configuration
├── data/                     # Data files
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Multi-container setup
├── requirements.txt          # Python dependencies
├── main.py                   # Entry point
├── README.md                 # Documentation
├── .gitignore                # Git ignore rules
└── tests/                    # Tests
```

---

## .gitignore Configuration

Make sure sensitive files aren't uploaded:

```bash
# Create/update .gitignore
cat > .gitignore << 'EOF'
# Environment variables
.env
.env.local
.env.*.local

# Credentials
credentials.json
**/secrets/
*.key
*.pem

# Data files
data/email_sent_tracker.json
data/history.json
results/**/*.mp3
results/**/*.pdf

# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
logs/
*.log

# Temporary
tmp/
temp/
.DS_Store
tmpclaude-*

# Large files
models/
results/reports/*.mp3
EOF

git add .gitignore
git commit -m "Update gitignore for sensitive files"
git push
```

---

## Deployment Checklist

- [ ] GitHub account created
- [ ] Repository created on GitHub
- [ ] Git remote added (`git remote -v` shows origin)
- [ ] Code pushed to GitHub (`git push`)
- [ ] README.md with instructions
- [ ] .gitignore configured
- [ ] GitHub Secrets added (SMTP credentials)
- [ ] Dockerfile verified
- [ ] Docker workflow created
- [ ] Deployment platform selected (Railway/Render/etc)
- [ ] Environment variables configured on platform
- [ ] Scheduled workflow created (if desired)
- [ ] First automated run verified

---

## Verification Steps

After pushing:

```bash
# 1. Check git status
git status

# 2. View recent commits
git log --oneline | head -5

# 3. Check remote
git remote -v

# 4. Verify on GitHub
# Visit: https://github.com/YOUR_USERNAME/GenerativeAI-agent
# Should see all files and latest commit
```

---

## Troubleshooting

### "Permission denied (publickey)"
→ Use HTTPS instead of SSH, or setup SSH key properly

### "fatal: remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/USERNAME/GenerativeAI-agent.git
```

### "Authentication failed"
→ Use Personal Access Token, not password
→ Create at: https://github.com/settings/tokens/new

### Docker build fails on GitHub
→ Check Docker layer caching
→ Verify requirements.txt is valid
→ Check .dockerignore for excluded files

---

## Next Steps

1. **Choose deployment platform** (Railway recommended)
2. **Run quick push test** (steps above)
3. **Verify on GitHub** (repo should be visible)
4. **Configure secrets** (SMTP credentials)
5. **Deploy to production** (platform-specific)
6. **Test automated runs** (manual trigger first)

---

## Recommended Reading

- GitHub Docs: https://docs.github.com
- Railway Docs: https://docs.railway.app
- Docker Docs: https://docs.docker.com
- GitHub Actions: https://docs.github.com/en/actions

---

**Need help? Let me know:**
- GitHub username for verification
- Which deployment platform you prefer
- Whether you want continuous deployment or scheduled runs
