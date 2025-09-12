# ✅ CORRECTED Render Setup Instructions

## Backend Web Service - CORRECT Settings

When creating the backend Web Service on Render, use these **EXACT** settings:

### Basic Info
- **Name**: `excel-transformer-backend`
- **Region**: Choose closest to your users
- **Branch**: `main` 
- **Root Directory**: `backend`

### Build & Deploy
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --config gunicorn.conf.py app:app`

### Environment Variables
Add these environment variables:
```
FLASK_ENV=production
FLASK_APP=app.py
```

### Advanced Settings
- **Health Check Path**: `/health`
- **Auto-Deploy**: `Yes`

## Why This Works Now

✅ **Fixed Issue**: `requirements.txt` is now in the `backend/` folder  
✅ **Correct Build Command**: No more `../requirements.txt` path error  
✅ **Production Server**: Using gunicorn instead of Flask dev server  

## Frontend Static Site - Settings

### Basic Info
- **Name**: `excel-transformer-frontend`  
- **Branch**: `main`
- **Root Directory**: `frontend`

### Build Settings
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `build`
- **Auto-Deploy**: `Yes`

## Step-by-Step Deploy Process

1. **Deploy Backend First**:
   - Create Web Service with settings above
   - Wait for deployment (5-10 minutes)  
   - Note your backend URL: `https://excel-transformer-backend-XXXX.onrender.com`

2. **Update Frontend API URL**:
   ```bash
   cd excel-transformer
   # Edit frontend/.env.production
   # Change to: REACT_APP_API_URL=https://your-actual-backend-url.onrender.com
   ```

3. **Push Update**:
   ```bash
   git add .
   git commit -m "Fix deployment paths and update API URL"
   git push origin main
   ```

4. **Deploy Frontend**:
   - Create Static Site with settings above
   - Wait for deployment (3-5 minutes)

Your app will be live! 🚀