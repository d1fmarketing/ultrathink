#!/bin/bash

# ULTRATHINK GitHub Repository Setup Script

echo "==============================================="
echo "🧠 ULTRATHINK GitHub Repository Setup"
echo "==============================================="
echo ""
echo "This script will help you push ULTRATHINK to GitHub"
echo ""

# Check if git is configured
if ! git config user.name > /dev/null 2>&1; then
    echo "Please configure git first:"
    echo "  git config --global user.name 'Your Name'"
    echo "  git config --global user.email 'your.email@example.com'"
    exit 1
fi

echo "📝 MANUAL STEPS TO CREATE GITHUB REPOSITORY:"
echo ""
echo "1. Go to https://github.com/new"
echo "2. Repository name: ultrathink"
echo "3. Description: 🧠 Distributed AI Trading System with ASI/HRM/MCTS"
echo "4. Set to Public or Private as desired"
echo "5. DO NOT initialize with README (we already have one)"
echo "6. Click 'Create repository'"
echo ""
echo "================================================"
echo ""
read -p "Press Enter when you've created the repository on GitHub..."
echo ""

# Get GitHub username
read -p "Enter your GitHub username: " GITHUB_USER

# Add remote and push
echo ""
echo "Adding remote and pushing to GitHub..."
git remote add origin "https://github.com/${GITHUB_USER}/ultrathink.git"
git branch -M main
git push -u origin main

echo ""
echo "✅ ULTRATHINK has been pushed to GitHub!"
echo "🔗 Repository URL: https://github.com/${GITHUB_USER}/ultrathink"
echo ""
echo "📊 Repository contains:"
echo "  - 7 EC2 instance configurations"
echo "  - ASI/HRM/MCTS AI components"
echo "  - Trinity scalper integration"
echo "  - Data collectors and ML farm"
echo "  - Complete documentation"
echo ""
echo "🚀 Next steps:"
echo "  1. Add collaborators: Settings → Manage access"
echo "  2. Set up Actions for CI/CD"
echo "  3. Create releases for stable versions"
echo "  4. Add topics: ai, trading, alphago, mcts"
echo ""
echo "==============================================="