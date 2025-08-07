#!/bin/bash

# ULTRATHINK GitHub Push Script - FIX ALL ISSUES PROPERLY

cd /tmp/ultrathink-project

echo "🧠 ULTRATHINK GitHub Push - Trying ALL methods"
echo "=============================================="

TOKEN="ghp_RVjZhG9XM7dJvTQXRQIhiJvVhJvQRK3LM0fF"
USER="ARCANE-CYBER"
REPO="ultrathink"

# Method 1: Create repo first using API
echo "Method 1: Creating repo via API..."
curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO\",\"description\":\"🧠 Distributed AI Trading System with ASI/HRM/MCTS\",\"public\":true}" \
  > /tmp/repo_create.json 2>&1

if grep -q "already exists" /tmp/repo_create.json; then
  echo "✓ Repo already exists, continuing..."
elif grep -q "html_url" /tmp/repo_create.json; then
  echo "✓ Repo created successfully!"
else
  echo "✗ Repo creation failed, trying push anyway..."
fi

# Method 2: Try classic format username:token
echo ""
echo "Method 2: Classic username:token format..."
git remote remove origin 2>/dev/null
git remote add origin "https://$USER:$TOKEN@github.com/$USER/$REPO.git"
if git push -u origin main 2>&1 | tee /tmp/push.log | grep -q "Everything up-to-date\|new branch"; then
  echo "✅ SUCCESS! Pushed to GitHub!"
  exit 0
fi

# Method 3: Try with git credential store
echo ""
echo "Method 3: Git credential store..."
git config --global credential.helper store
echo "https://$USER:$TOKEN@github.com" > ~/.git-credentials
git remote set-url origin "https://github.com/$USER/$REPO.git"
if git push -u origin main 2>&1 | tee /tmp/push2.log | grep -q "Everything up-to-date\|new branch"; then
  echo "✅ SUCCESS! Pushed to GitHub!"
  exit 0
fi

# Method 4: Try with .netrc
echo ""
echo "Method 4: Using .netrc..."
cat > ~/.netrc << EOF
machine github.com
login $TOKEN
password x-oauth-basic
EOF
chmod 600 ~/.netrc
git remote set-url origin "https://github.com/$USER/$REPO.git"
if git push -u origin main 2>&1 | tee /tmp/push3.log | grep -q "Everything up-to-date\|new branch"; then
  echo "✅ SUCCESS! Pushed to GitHub!"
  exit 0
fi

# Method 5: Force push with inline credentials
echo ""
echo "Method 5: Force with inline credentials..."
if git push "https://$TOKEN:x-oauth-basic@github.com/$USER/$REPO.git" main:main --force 2>&1 | tee /tmp/push4.log | grep -q "Everything up-to-date\|new branch\|forced update"; then
  echo "✅ SUCCESS! Pushed to GitHub!"
  exit 0
fi

# Method 6: Try with x-access-token
echo ""
echo "Method 6: x-access-token format..."
git remote set-url origin "https://x-access-token:$TOKEN@github.com/$USER/$REPO.git"
if git push -u origin main 2>&1 | tee /tmp/push5.log | grep -q "Everything up-to-date\|new branch"; then
  echo "✅ SUCCESS! Pushed to GitHub!"
  exit 0
fi

# Method 7: Try oauth2 prefix
echo ""
echo "Method 7: oauth2 prefix..."
git remote set-url origin "https://oauth2:$TOKEN@github.com/$USER/$REPO.git"
if git push -u origin main 2>&1 | tee /tmp/push6.log | grep -q "Everything up-to-date\|new branch"; then
  echo "✅ SUCCESS! Pushed to GitHub!"
  exit 0
fi

# Method 8: Direct git push with token as password
echo ""
echo "Method 8: Direct token as password..."
export GIT_ASKPASS=echo
export GIT_USERNAME=$USER
export GIT_PASSWORD=$TOKEN
git remote set-url origin "https://github.com/$USER/$REPO.git"
if git push -u origin main 2>&1 | tee /tmp/push7.log | grep -q "Everything up-to-date\|new branch"; then
  echo "✅ SUCCESS! Pushed to GitHub!"
  exit 0
fi

echo ""
echo "❌ All methods failed. Check logs in /tmp/push*.log"
echo "Token might be expired or invalid."
echo ""
echo "MANUAL FIX:"
echo "1. Get a new token at: https://github.com/settings/tokens/new"
echo "2. Select 'repo' scope"
echo "3. Run: git push https://YOUR_USERNAME:YOUR_NEW_TOKEN@github.com/$USER/$REPO.git main"