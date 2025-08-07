#!/usr/bin/env python3
"""
Create ULTRATHINK GitHub Repository
"""

import json
import os
import subprocess
import sys

def create_github_repo():
    """Create GitHub repository and push code"""
    
    print("🧠 ULTRATHINK GitHub Repository Creator")
    print("=" * 50)
    
    # Get GitHub token
    token = input("Enter your GitHub Personal Access Token: ").strip()
    if not token:
        print("❌ Token is required!")
        print("\nTo create a token:")
        print("1. Go to https://github.com/settings/tokens/new")
        print("2. Select 'repo' scope")
        print("3. Click 'Generate token'")
        return
    
    # Get username
    username = input("Enter your GitHub username: ").strip()
    if not username:
        print("❌ Username is required!")
        return
    
    print("\n📦 Creating repository...")
    
    # Create repo using curl
    cmd = f'''curl -X POST \
        -H "Authorization: token {token}" \
        -H "Accept: application/vnd.github.v3+json" \
        https://api.github.com/user/repos \
        -d '{{"name": "ultrathink", 
              "description": "🧠 Distributed AI Trading System with ASI/HRM/MCTS - AlphaGo-inspired trading intelligence", 
              "public": true,
              "has_issues": true,
              "has_projects": true,
              "has_wiki": true}}' '''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if "already exists" in result.stderr or "already exists" in result.stdout:
        print("⚠️  Repository already exists, continuing...")
    elif result.returncode != 0:
        print(f"❌ Failed to create repository: {result.stderr}")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    else:
        print("✅ Repository created successfully!")
    
    # Configure git remote
    print("\n🔗 Configuring git remote...")
    os.chdir('/tmp/ultrathink-project')
    
    # Remove existing remote if present
    subprocess.run("git remote remove origin", shell=True, stderr=subprocess.DEVNULL)
    
    # Add new remote
    subprocess.run(f"git remote add origin https://github.com/{username}/ultrathink.git", shell=True)
    
    # Set branch to main
    subprocess.run("git branch -M main", shell=True)
    
    # Push to GitHub
    print("\n📤 Pushing to GitHub...")
    push_cmd = f"git push -u https://{token}@github.com/{username}/ultrathink.git main"
    result = subprocess.run(push_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("\n✅ SUCCESS! ULTRATHINK has been pushed to GitHub!")
        print(f"\n🔗 Repository URL: https://github.com/{username}/ultrathink")
        print("\n📊 Repository contains:")
        print("  ✅ 7 EC2 instance configurations")
        print("  ✅ ASI/HRM/MCTS AI components")
        print("  ✅ Trinity scalper integration")
        print("  ✅ Data collectors and ML farm")
        print("  ✅ Complete documentation")
        print("\n🚀 Next steps:")
        print(f"  1. View your repo: https://github.com/{username}/ultrathink")
        print("  2. Add collaborators in Settings → Manage access")
        print("  3. Set up GitHub Actions for CI/CD")
        print("  4. Create releases for stable versions")
        print("  5. Add topics: ai, trading, alphago, mcts, distributed-systems")
    else:
        print(f"❌ Push failed: {result.stderr}")
        print("\nTry manual push:")
        print(f"  cd /tmp/ultrathink-project")
        print(f"  git push -u origin main")

if __name__ == "__main__":
    create_github_repo()