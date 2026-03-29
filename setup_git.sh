#!/bin/bash
# =====================================================
# SIKH - Git Repository Initializer
# Run this ONCE after cloning or creating the repo
# =====================================================

echo "🚀 Initializing SIKH Git Repository..."

# Init git
git init
git add .
git commit -m "feat: initial project structure — all modules scaffolded"

# Create and push main branch
git branch -M main

echo ""
echo "📌 Now push to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/SIKH.git"
echo "   git push -u origin main"
echo ""

# Create dev branch
git checkout -b dev
git push origin dev 2>/dev/null || echo "   (push dev after setting remote)"

# Create feature branches
git checkout -b feature/backend
git push origin feature/backend 2>/dev/null || echo "   (push feature/backend after setting remote)"

git checkout -b feature/ai
git push origin feature/ai 2>/dev/null || echo "   (push feature/ai after setting remote)"

git checkout -b feature/frontend
git push origin feature/frontend 2>/dev/null || echo "   (push feature/frontend after setting remote)"

# Return to dev
git checkout dev

echo ""
echo "✅ Branches created:"
echo "   main            — stable releases only"
echo "   dev             — integration branch"
echo "   feature/backend — Member 1 (you)"
echo "   feature/ai      — Member 2"
echo "   feature/frontend — Member 3"
echo ""
echo "📋 Share these instructions with your team:"
echo "   git clone https://github.com/YOUR_USERNAME/SIKH.git"
echo "   cd SIKH"
echo "   git checkout feature/their-branch"
echo ""
echo "🎉 Done! You're ready to build SIKH."
