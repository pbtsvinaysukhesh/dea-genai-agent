# GitHub Upload - Quick Reference

## 5-Minute Quick Start

### 1. Create GitHub Repository
Go to: **https://github.com/new**
- Name: `GenerativeAI-agent`
- Visibility: Private (recommended) or Public
- Don't initialize (we have commits)
- Click **Create repository**

### 2. Run Setup Script
```bash
python github_setup.py
```

This will guide you through:
- ✓ Verifying git repository
- ✓ Checking uncommitted changes
- ✓ Configuring remote URL
- ✓ Verifying main branch
- ✓ Pushing code to GitHub

### 3. OR Manual Setup (If Preferred)

**For HTTPS (simpler):**
```bash
# Replace YOUR_USERNAME
git remote add origin https://github.com/YOUR_USERNAME/GenerativeAI-agent.git
git branch -M main
git push -u origin main
```

**For SSH (more secure):**
```bash
git remote add origin git@github.com:YOUR_USERNAME/GenerativeAI-agent.git
git branch -M main
git push -u origin main
```

### 4. Verify on GitHub
Visit: `https://github.com/YOUR_USERNAME/GenerativeAI-agent`

You should see all your files!

---

## Choose Your Hosting

### Option 1: Railway.app (⭐ EASIEST)
1. Go to https://railway.app
2. Sign in with GitHub
3. New Project → Deploy from GitHub repo
4. Select `GenerativeAI-agent`
5. Add environment variables (SMTP settings)
6. Click Deploy → Done!

**Cost:** Free tier available, then $5-20/month

### Option 2: GitHub Actions (🔄 SCHEDULED)
Runs automatically daily:
- Already configured in `.github/workflows/`
- Runs pipeline, generates reports
- Sends emails automatically

**Cost:** Free (up to 2,000 minutes/month)

### Option 3: Docker + Any Cloud
Use the included `Dockerfile` and `docker-compose.yml`
- **Google Cloud Run**
- **AWS Lambda**
- **Azure Container Instances**
- **Heroku** (paid)

**Cost:** Varies ($5-30+/month)

---

## First-Time HTTPS Push (Most Common)

```bash
# Step 1: Configure git
git remote add origin https://github.com/YOUR_USERNAME/GenerativeAI-agent.git
git branch -M main

# Step 2: Push
git push -u origin main

# Step 3: When prompted for password:
# Username: YOUR_GITHUB_USERNAME
# Password: PERSONAL_ACCESS_TOKEN (see below)
```

### Generate Personal Access Token:
1. Go to: https://github.com/settings/tokens/new
2. Click "Generate new token"
3. Check these scopes:
   - [x] repo
   - [x] workflow
   - [x] gist
4. Click "Generate token"
5. Copy the token (you'll only see it once!)
6. Use as password in git push

---

## Troubleshooting

### "fatal: remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/GenerativeAI-agent.git
git push -u origin main
```

### "Permission denied (publickey)" (SSH error)
→ Use HTTPS instead:
```bash
git remote set-url origin https://github.com/YOUR_USERNAME/GenerativeAI-agent.git
```

### "Authentication failed" (HTTPS error)
→ Use Personal Access Token (not GitHub password)
→ Create one: https://github.com/settings/tokens/new

### "Branch is master not main"
```bash
git branch -M main
git push -u origin main
```

---

## After Push: Setup Optional Features

### Add GitHub Secrets (For Automated Email)
1. Go to Your Repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each one:
   ```
   SMTP_SERVER = smtp.gmail.com
   SMTP_PORT = 587
   SMTP_USER = your-email@gmail.com
   SMTP_PASSWORD = your-app-password
   ```

### Enable GitHub Actions
1. Go to Actions tab
2. Click "I understand my workflows, go ahead and enable them"
3. Workflows will run on schedule automatically

### Deploy to Railway
1. Go to https://railway.app
2. Sign in with GitHub
3. New Project
4. Deploy from GitHub repo
5. Select your repo
6. Railway auto-detects Dockerfile
7. Add environment variables (same SMTP secrets)
8. Click Deploy!

---

## File Structure on GitHub

Your repository will look like:
```
GenerativeAI-agent/
├── .github/
│   └── workflows/          # Automated tasks
├── src/                    # Python code
│   ├── multiformat_integration.py
│   ├── pdf_generator.py
│   ├── podcast_generator.py
│   └── ... (30+ more files)
├── Dashboard/              # Web interface
├── config/                 # Configuration
├── Dockerfile              # Docker setup
├── docker-compose.yml      # Multi-container
├── main.py                 # Entry point
├── requirements.txt        # Python packages
└── README.md              # Documentation
```

---

## What Gets Public vs Private

**If Repository is PUBLIC:**
- ✓ All code visible
- ✓ Ready for open-source
- ✓ Others can fork/contribute

**If Repository is PRIVATE:**
- ✓ Only you can see
- ✓ Still deployable
- ✓ Recommended for sensitive data

**Either way, GitHub Secrets are PRIVATE:**
- ✓ SMTP passwords never exposed
- ✓ Credentials encrypted
- ✓ Safe for production

---

## Next Steps (In Order)

1. **Create GitHub repo** (https://github.com/new)
2. **Run setup script or manual push**
   ```bash
   python github_setup.py
   # OR
   git remote add origin https://github.com/YOUR_USERNAME/GenerativeAI-agent.git
   git branch -M main
   git push -u origin main
   ```
3. **Verify on GitHub** (visit your repo URL)
4. **Add SMTP secrets** (Settings → Secrets)
5. **Test a push** (make a change, commit, push)
6. **Deploy to production** (Railway/Actions/Cloud)
7. **Monitor automated runs** (Actions tab)

---

## Command Cheat Sheet

```bash
# View remote
git remote -v

# Change remote URL
git remote set-url origin https://github.com/NEW_URL

# Check branch
git branch

# Rename to main if needed
git branch -M main

# Push
git push -u origin main

# Check recent pushes
git log --oneline | head -10

# View GitHub Actions status
# → Visit: https://github.com/YOUR_USERNAME/GenerativeAI-agent/actions
```

---

## Support Resources

- **GitHub Help:** https://docs.github.com
- **Railway Docs:** https://docs.railway.app
- **Docker Docs:** https://docs.docker.com
- **GitHub Actions:** https://docs.github.com/en/actions

---

## Estimated Timeline

| Task | Time |
|------|------|
| Create GitHub repo | 2 min |
| Push code | 1-5 min |
| Configure secrets | 3 min |
| Deploy to Railway | 5 min |
| Verify running | 2 min |
| **Total** | **~15 min** |

---

**Ready to upload? Start with Step 1 above or run: `python github_setup.py`**
