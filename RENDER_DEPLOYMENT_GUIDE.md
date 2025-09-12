# Render Deployment Guide - Excel Template Transformer

## Overview

You'll need to deploy **TWO separate services** on Render:
1. **Backend Web Service** (Flask API)
2. **Frontend Static Site** (React App)

## Prerequisites

- GitHub account
- Render account (free tier works)
- Your code pushed to a GitHub repository

## Step 1: Prepare Your Repository

### 1.1 Push to GitHub
```bash
cd excel-transformer
git init
git add .
git commit -m "Initial commit - Excel Template Transformer"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/excel-transformer.git
git push -u origin main
```

### 1.2 Repository Structure
Ensure your repo has this structure:
```
excel-transformer/
├── backend/
│   ├── app.py
│   ├── render.yaml
│   └── gunicorn.conf.py
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── render.yaml
│   ├── .env.production
│   └── _redirects
└── requirements.txt
```

## Step 2: Deploy Backend (Web Service)

### 2.1 Create Backend Service
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:

**Basic Settings:**
- **Name**: `excel-transformer-backend`
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Root Directory**: `backend`
- **Runtime**: `Python 3`

**Build & Deploy:**
- **Build Command**: `pip install -r ../requirements.txt`
- **Start Command**: `gunicorn --config gunicorn.conf.py app:app`

**Environment Variables:**
```
FLASK_ENV=production
FLASK_APP=app.py
```

### 2.2 Deploy Backend
1. Click **"Create Web Service"**
2. Wait for deployment (5-10 minutes)
3. Note your backend URL: `https://excel-transformer-backend-XXXX.onrender.com`

### 2.3 Test Backend
```bash
# Health check
curl https://your-backend-url.onrender.com/health

# Should return: {"status": "healthy", "timestamp": "..."}
```

## Step 3: Update Frontend Configuration

### 3.1 Update API URL
Edit `frontend/.env.production`:
```env
REACT_APP_API_URL=https://your-actual-backend-url.onrender.com
```

### 3.2 Commit Changes
```bash
git add frontend/.env.production
git commit -m "Update production API URL"
git push origin main
```

## Step 4: Deploy Frontend (Static Site)

### 4.1 Create Frontend Service
1. In Render Dashboard, click **"New +"** → **"Static Site"**
2. Connect your GitHub repository
3. Configure the service:

**Basic Settings:**
- **Name**: `excel-transformer-frontend`
- **Branch**: `main`
- **Root Directory**: `frontend`

**Build Settings:**
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `build`

**Headers (Optional):**
```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
```

### 4.2 Deploy Frontend
1. Click **"Create Static Site"**
2. Wait for deployment (3-5 minutes)
3. Your app URL: `https://excel-transformer-frontend-XXXX.onrender.com`

## Step 5: Test Complete Application

### 5.1 Access Your App
1. Open your frontend URL in browser
2. You should see the Excel Template Transformer interface
3. Check that "Backend Online" indicator shows green

### 5.2 Test Upload Flow
1. Upload a test Excel file
2. Verify processing works
3. Download transformed file
4. Confirm transformations are correct

## Step 6: Custom Domain (Optional)

### 6.1 Frontend Custom Domain
1. In Render Dashboard → Your Static Site
2. Go to **Settings** → **Custom Domains**
3. Add your domain (e.g., `excel-transformer.yourdomain.com`)
4. Update DNS with provided CNAME

### 6.2 Backend Custom Domain
1. In Render Dashboard → Your Web Service  
2. Go to **Settings** → **Custom Domains**
3. Add subdomain (e.g., `api.yourdomain.com`)
4. Update frontend `.env.production` with custom API URL

## Troubleshooting

### Common Issues

**Backend Build Fails:**
```bash
# Check requirements.txt is in root directory
# Ensure Python version compatibility
# Check build logs in Render dashboard
```

**Frontend Build Fails:**
```bash
# Verify package.json is correct
# Check Node.js version compatibility
# Ensure all dependencies are listed
```

**CORS Errors:**
```python
# In backend/app.py, ensure CORS is configured:
from flask_cors import CORS
CORS(app)
```

**File Upload Issues:**
```python
# Check file size limits in Render (max 100MB)
# Verify temporary directory permissions
# Check timeout settings in gunicorn.conf.py
```

**API Connection Issues:**
```javascript
// Check .env.production has correct backend URL
// Verify backend is deployed and healthy
// Check browser network tab for CORS/404 errors
```

### Performance Considerations

**Free Tier Limitations:**
- Backend may sleep after 15 minutes of inactivity
- First request after sleep takes 30-60 seconds
- 750 build hours/month limit
- 100GB bandwidth/month

**Optimization Tips:**
- Use Render's paid tier for production
- Implement file size limits
- Add request timeout handling
- Consider file cleanup cron jobs

## Monitoring & Logs

### Backend Logs
1. Render Dashboard → Web Service → Logs
2. View real-time application logs
3. Monitor error patterns and performance

### Frontend Analytics
1. Render Dashboard → Static Site → Analytics
2. View traffic patterns and performance
3. Monitor build success/failure rates

## Environment Variables Reference

### Backend (.env or Render Environment Variables)
```env
FLASK_ENV=production
FLASK_APP=app.py
PORT=10000
```

### Frontend (.env.production)
```env
REACT_APP_API_URL=https://your-backend-url.onrender.com
```

## Security Considerations

1. **HTTPS Only**: Render provides free SSL certificates
2. **CORS Configuration**: Restrict origins in production
3. **File Upload Limits**: Implement size and type restrictions
4. **Rate Limiting**: Consider adding request rate limiting
5. **Input Validation**: Ensure all inputs are validated server-side

## Cost Estimation

**Free Tier (Development):**
- Backend Web Service: Free (with sleep)
- Frontend Static Site: Free
- Custom domains: Free
- Total: $0/month

**Paid Tier (Production):**
- Backend Web Service: $7/month (no sleep)
- Frontend Static Site: Free
- Total: $7/month

## Next Steps After Deployment

1. **Monitor Usage**: Track file uploads and processing times
2. **Add Analytics**: Implement user analytics if needed
3. **Performance Optimization**: Monitor and optimize slow operations
4. **Feature Enhancement**: Add new transformations based on user feedback
5. **Backup Strategy**: Implement data backup for important configurations