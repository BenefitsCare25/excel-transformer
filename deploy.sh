#!/bin/bash

# Deployment script for Excel Template Transformer

echo "🚀 Preparing Excel Template Transformer for deployment..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
    git branch -M main
fi

# Add all files
echo "📁 Adding files to git..."
git add .

# Commit changes
echo "💾 Committing changes..."
git commit -m "Deploy: Excel Template Transformer for Render" || echo "No changes to commit"

# Check if remote is set
if ! git remote | grep -q origin; then
    echo "⚠️  Please add your GitHub remote:"
    echo "git remote add origin https://github.com/YOUR_USERNAME/excel-transformer.git"
    echo ""
    echo "Then run: git push -u origin main"
else
    echo "⬆️  Pushing to GitHub..."
    git push origin main
    
    echo ""
    echo "✅ Repository updated!"
    echo ""
    echo "🎯 Next steps:"
    echo "1. Go to https://dashboard.render.com"
    echo "2. Create Web Service (Backend):"
    echo "   - Name: excel-transformer-backend" 
    echo "   - Root Directory: backend"
    echo "   - Build Command: pip install -r ../requirements.txt"
    echo "   - Start Command: gunicorn --config gunicorn.conf.py app:app"
    echo ""
    echo "3. Create Static Site (Frontend):"
    echo "   - Name: excel-transformer-frontend"
    echo "   - Root Directory: frontend" 
    echo "   - Build Command: npm install && npm run build"
    echo "   - Publish Directory: build"
    echo ""
    echo "📖 See RENDER_DEPLOYMENT_GUIDE.md for detailed instructions"
fi