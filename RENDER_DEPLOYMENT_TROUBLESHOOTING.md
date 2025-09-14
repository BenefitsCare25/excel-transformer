# Render Deployment Troubleshooting Guide

## Common Issues & Solutions

### 1. **Long Deployment Times (10+ minutes)**

**Cause**: Recent multi-file upload feature added threading dependencies that may not be available or cause import delays.

**Solutions Applied**:
- ✅ Added graceful fallback for `concurrent.futures` imports
- ✅ Reduced max workers from 3 to 2 for free tier memory limits
- ✅ Sequential processing fallback if concurrent processing unavailable
- ✅ Optimized Gunicorn config for free tier resources

### 2. **Memory Issues on Free Tier**

**Optimizations**:
- ✅ Reduced worker connections from 1000 to 500
- ✅ More frequent worker restarts (500 requests vs 1000)
- ✅ Added `preload_app = True` for memory efficiency
- ✅ Use RAM disk for temporary files (`/dev/shm`)

### 3. **Build Command Issues**

**Improvements**:
- ✅ Added `pip install --upgrade pip`
- ✅ Use `--no-cache-dir` to prevent cache issues
- ✅ Added `--check-config` to catch config errors early
- ✅ Added `PYTHONUNBUFFERED=1` for better logging

### 4. **Startup Diagnostics**

**Added Logging**:
- ✅ Startup check function with detailed logging
- ✅ Python version and environment information
- ✅ Concurrent processing availability check
- ✅ Graceful error handling for geocoding service

## Deployment Monitoring Commands

### Check Render Logs
```bash
# In Render dashboard -> Logs tab, look for:
# "Starting Excel Transformer Backend..."
# "Concurrent processing: enabled/disabled"
# "Startup checks completed successfully"
```

### Local Testing
```bash
cd backend
python app.py  # Should show startup diagnostics
```

### Health Check
```bash
curl https://your-render-url.onrender.com/health
```

## Emergency Rollback

If deployment still fails, rollback to previous version:
```bash
git revert HEAD  # Revert latest changes
git push         # Deploy previous stable version
```

## Free Tier Limitations

- **Memory**: 512MB RAM (shared with concurrent processing)
- **CPU**: 0.1 CPU units (limits concurrent workers)
- **Timeout**: 30 seconds for HTTP responses
- **Build Time**: 15 minutes max

## Performance Monitoring

Monitor these metrics in Render dashboard:
- **Build Time**: Should be < 5 minutes after optimizations
- **Memory Usage**: Should stay < 400MB
- **Response Time**: Should be < 30 seconds for single files
- **Error Rate**: Should be < 5%