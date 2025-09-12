# Render Deployment - Quick Start

## Answer: You need **Web Services** (not Static Pages)

You'll deploy **TWO services**:
1. **Backend**: Web Service (Flask API)  
2. **Frontend**: Static Site (React App)

## Quick Deploy Steps

### 1. Push to GitHub
```bash
cd excel-transformer
git init
git add .
git commit -m "Deploy to Render"
git remote add origin https://github.com/YOUR_USERNAME/excel-transformer.git
git push -u origin main
```

### 2. Deploy Backend (Web Service)
- Go to [Render Dashboard](https://dashboard.render.com)
- **New +** → **Web Service** → Connect GitHub
- **Settings**:
  - Name: `excel-transformer-backend`
  - Root Directory: `backend`
  - Build Command: `pip install -r ../requirements.txt`  
  - Start Command: `gunicorn --config gunicorn.conf.py app:app`
  - Environment Variables:
    ```
    FLASK_ENV=production
    FLASK_APP=app.py
    ```

### 3. Get Backend URL & Update Frontend
- Note your backend URL: `https://excel-transformer-backend-XXXX.onrender.com`
- Update `frontend/.env.production`:
  ```env
  REACT_APP_API_URL=https://excel-transformer-backend-XXXX.onrender.com
  ```
- Push update:
  ```bash
  git add frontend/.env.production
  git commit -m "Update API URL"
  git push origin main
  ```

### 4. Deploy Frontend (Static Site)
- **New +** → **Static Site** → Connect GitHub
- **Settings**:
  - Name: `excel-transformer-frontend`
  - Root Directory: `frontend`
  - Build Command: `npm install && npm run build`
  - Publish Directory: `build`

### 5. Done! 
Your app will be live at: `https://excel-transformer-frontend-XXXX.onrender.com`

## Service Types Explained

| Service Type | Use Case | Your App |
|-------------|----------|----------|
| **Web Service** | Backend APIs, databases | ✅ Flask backend |
| **Static Site** | Frontend apps, websites | ✅ React frontend |
| **Background Worker** | Scheduled jobs | ❌ Not needed |
| **Private Service** | Internal services | ❌ Not needed |

## Cost (Free Tier)
- Backend Web Service: **Free** (sleeps after 15min idle)
- Frontend Static Site: **Free** 
- Total: **$0/month**

**Upgrade to $7/month** to prevent backend sleeping in production.

## Troubleshooting

**Common Issues:**
- Build fails → Check `requirements.txt` and `package.json`
- CORS errors → Ensure `flask-cors` is installed
- File upload fails → Check file size limits (100MB max)

**Need Help?** See the complete `RENDER_DEPLOYMENT_GUIDE.md` for detailed instructions.