#!/usr/bin/env python
"""
GitHub Setup Helper
Guides you through uploading your project to GitHub
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return output"""
    print(f"\n[EXECUTING] {description or cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] {result.stderr}")
            return False, result.stderr
        if result.stdout:
            print(f"[OUTPUT] {result.stdout.strip()}")
        return True, result.stdout
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return False, str(e)


def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║        GitHub Upload & Hosting Setup Guide                    ║
║   For: GenerativeAI-agent Multi-Format Reports System         ║
╚════════════════════════════════════════════════════════════════╝
    """)

    # Step 1: Verify we're in git repo
    print("\n[STEP 1] Verifying Git Repository")
    if not os.path.exists(".git"):
        print("[ERROR] Not in a git repository!")
        sys.exit(1)
    print("[OK] Git repository found")

    # Step 2: Check git status
    print("\n[STEP 2] Checking Repository Status")
    success, output = run_command(
        "git status --short",
        "Checking for uncommitted changes"
    )
    if output.strip():
        print("[WARNING] There are uncommitted changes:")
        print(output)
        response = input("\nCommit these changes now? (y/n): ")
        if response.lower() == 'y':
            run_command(
                'git add . && git commit -m "Latest updates before GitHub push"',
                "Committing changes"
            )
    else:
        print("[OK] Working directory is clean")

    # Step 3: Get GitHub info
    print("\n[STEP 3] GitHub Account Information")
    username = input("Enter your GitHub username: ").strip()
    repo_name = input("Enter repository name (default: GenerativeAI-agent): ").strip() or "GenerativeAI-agent"
    use_https = input("Use HTTPS (y/n)? [Default: y]: ").strip().lower() != 'n'

    # Step 4: Configure remote
    print("\n[STEP 4] Configuring Git Remote")

    # Check if remote exists
    success, output = run_command("git remote -v", "Checking existing remotes")

    if "origin" in output:
        print("[WARNING] Remote 'origin' already exists:")
        print(output)
        response = input("Remove and reconfigure? (y/n): ")
        if response.lower() == 'y':
            run_command("git remote remove origin", "Removing existing remote")
        else:
            print("[OK] Using existing remote")
            return verify_and_push()

    # Add new remote
    if use_https:
        remote_url = f"https://github.com/{username}/{repo_name}.git"
    else:
        remote_url = f"git@github.com:{username}/{repo_name}.git"

    print(f"\nConfiguring remote URL: {remote_url}")
    success, _ = run_command(
        f"git remote add origin {remote_url}",
        "Adding remote origin"
    )

    if not success:
        print("[ERROR] Failed to add remote")
        sys.exit(1)

    # Step 5: Verify main branch
    print("\n[STEP 5] Verifying Main Branch")
    success, output = run_command("git branch", "Checking current branch")

    if "master" in output and "main" not in output:
        print("[WARNING] Branch is 'master', renaming to 'main'...")
        run_command("git branch -M main", "Renaming to main")
    else:
        print("[OK] Main branch already configured")

    # Step 6: View commit history
    print("\n[STEP 6] Commit History")
    run_command("git log --oneline | head -5", "Showing recent commits")

    # Step 7: Prepare for push
    print("\n[STEP 7] Pre-Push Checklist")
    print("""
    Before pushing, ensure:
    ☐ You've created a repository on GitHub:
      https://github.com/new
    ☐ Repository name matches: {}
    ☐ You have GitHub credentials ready
    ☐ For HTTPS: Personal Access Token (not password)
    ☐ For SSH: SSH keys configured
    """.format(repo_name))

    response = input("\nReady to push? (y/n): ")
    if response.lower() != 'y':
        print("[INFO] Push cancelled")
        return False

    # Step 8: Push code
    print("\n[STEP 8] Pushing Code to GitHub")
    print(f"Pushing branch 'main' to {remote_url}...\n")

    success, output = run_command(
        "git push -u origin main",
        "Pushing code to GitHub"
    )

    if not success:
        print("[ERROR] Push failed!")
        if "Permission denied" in output:
            print("""
[INFO] Authentication failed. Troubleshooting:

For HTTPS:
  1. Generate token: https://github.com/settings/tokens/new
  2. Scopes: repo, workflow
  3. Use token as password when prompted

For SSH:
  1. Generate key: ssh-keygen -t ed25519 -C "your-email@example.com"
  2. Add to agent: ssh-add ~/.ssh/id_ed25519
  3. Add public key to GitHub: https://github.com/settings/keys
            """)
        sys.exit(1)

    # Step 9: Verify push
    print("\n[STEP 9] Verifying Push")
    success, output = run_command(
        "git remote -v",
        "Verifying remote configuration"
    )
    print(output)

    # Success!
    print("\n" + "="*60)
    print("[SUCCESS] Code pushed to GitHub!")
    print("="*60)

    print(f"""
Your repository is now on GitHub:
https://github.com/{username}/{repo_name}

Next steps:

1. VERIFY ON GITHUB
   Visit the URL above and verify all files are present

2. SETUP SECRETS (for automated deployments)
   Go to: Settings → Secrets and variables → Actions
   Add:
   - SMTP_SERVER
   - SMTP_PORT
   - SMTP_USER
   - SMTP_PASSWORD

3. CHOOSE DEPLOYMENT PLATFORM
   Option A: Railway.app (recommended)
     → Visit https://railway.app
     → Connect GitHub repo
     → Configure environment variables
     → Deploy!

   Option B: GitHub Actions (scheduled)
     → Already configured in .github/workflows/
     → Runs daily at 9 AM UTC

   Option C: Docker Hub + Kubernetes
     → Push Docker image to registry
     → Deploy with kubectl

4. TEST AUTOMATED DEPLOYMENT
   Trigger manually from GitHub Actions tab
   Or wait for scheduled run

For detailed instructions, see:
→ GITHUB_DEPLOYMENT_GUIDE.md

    """)

    response = input("Would you like to open GitHub now? (y/n): ")
    if response.lower() == 'y':
        import webbrowser
        webbrowser.open(f"https://github.com/{username}/{repo_name}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Setup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        sys.exit(1)
