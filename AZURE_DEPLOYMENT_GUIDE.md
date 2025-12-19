# Azure Deployment Guide

Complete step-by-step guide to deploy Excel Transformer to Azure App Service with GitHub integration.

---

## Prerequisites

1. **Azure Account**
   - Sign up at: https://azure.microsoft.com/free
   - Use your company email (e.g., yourname@company.com)
   - Get $200 free credits for 30 days

2. **GitHub Repository**
   - Your code is already on GitHub ✅
   - You have admin access to the repository

3. **Tools** (Optional - can use Azure Portal web interface)
   - Azure CLI: https://learn.microsoft.com/cli/azure/install-azure-cli
   - Git (already installed)

---

## Step 1: Create Azure App Service

### Option A: Using Azure Portal (Recommended for beginners)

1. **Login to Azure**
   - Go to: https://portal.azure.com
   - Sign in with your company email

2. **Create Resource Group**
   - Click "Resource groups" → "Create"
   - Name: `excel-transformer-rg`
   - Region: **Southeast Asia** (Singapore)
   - Click "Review + Create" → "Create"

3. **Create App Service**
   - Click "Create a resource" → "Web App"
   - Fill in details:
     ```
     Resource Group: excel-transformer-rg
     Name: excel-transformer (must be globally unique)
     Publish: Code
     Runtime stack: Python 3.11
     Operating System: Linux
     Region: Southeast Asia (Singapore)
     ```

4. **Choose Pricing Tier**
   - Click "Change size" under App Service Plan
   - Recommended: **B1 Basic** (~$15/month)
     - 1 core, 1.75 GB RAM
     - Custom domains
     - SSL/TLS support
   - For testing: **F1 Free** (limited features)
   - Click "Apply"

5. **Review and Create**
   - Click "Review + Create"
   - Click "Create"
   - Wait 2-3 minutes for deployment

### Option B: Using Azure CLI (Advanced)

```bash
# Login to Azure
az login

# Create resource group
az group create \
  --name excel-transformer-rg \
  --location southeastasia

# Create App Service Plan
az appservice plan create \
  --name excel-transformer-plan \
  --resource-group excel-transformer-rg \
  --location southeastasia \
  --is-linux \
  --sku B1

# Create Web App
az webapp create \
  --name excel-transformer \
  --resource-group excel-transformer-rg \
  --plan excel-transformer-plan \
  --runtime "PYTHON:3.11"
```

---

## Step 2: Configure GitHub Integration

### Method 1: Using Azure Portal (Easiest)

1. **Go to Deployment Center**
   - In Azure Portal, open your App Service
   - Click "Deployment Center" in left menu

2. **Connect GitHub**
   - Source: Select **GitHub**
   - Click "Authorize" → Login to GitHub
   - Grant Azure access to your repositories

3. **Configure Deployment**
   ```
   Organization: <your-github-username>
   Repository: EL (or your repo name)
   Branch: master (or main)
   Build Provider: GitHub Actions
   ```

4. **Save Configuration**
   - Click "Save"
   - Azure will automatically:
     - Create `.github/workflows/azure-deploy.yml`
     - Set up deployment secrets
     - Trigger first deployment

### Method 2: Using GitHub Actions (Already prepared)

1. **Get Publish Profile**
   - In Azure Portal → App Service
   - Click "Get publish profile" (top menu)
   - Download the `.PublishSettings` file

2. **Add GitHub Secret**
   - Go to your GitHub repository
   - Settings → Secrets and variables → Actions
   - Click "New repository secret"
   ```
   Name: AZURE_WEBAPP_PUBLISH_PROFILE
   Value: <paste entire content of .PublishSettings file>
   ```

3. **Update Workflow File**
   - Edit `.github/workflows/azure-deploy.yml`
   - Change `AZURE_WEBAPP_NAME` to your app name
   ```yaml
   env:
     AZURE_WEBAPP_NAME: excel-transformer  # Your unique name
   ```

4. **Push to GitHub**
   ```bash
   git add .
   git commit -m "feat: add Azure deployment configuration"
   git push origin master
   ```

5. **Monitor Deployment**
   - Go to GitHub → Actions tab
   - Watch the deployment progress
   - Deployment takes 3-5 minutes

---

## Step 3: Configure Environment Variables

### Add Required Environment Variables

1. **In Azure Portal**
   - Go to App Service → Configuration
   - Click "New application setting" for each:

   ```
   FLASK_ENV = production
   FLASK_APP = app.py
   PYTHONUNBUFFERED = 1

   # Optional: Google Maps API
   GOOGLE_MAPS_API_KEY = your_api_key_here

   # Optional: Custom paths
   UPLOAD_FOLDER = uploads
   PROCESSED_FOLDER = processed
   ```

2. **Click "Save"** → "Continue"
   - App will restart automatically

### Using Azure CLI

```bash
az webapp config appsettings set \
  --name excel-transformer \
  --resource-group excel-transformer-rg \
  --settings \
    FLASK_ENV=production \
    FLASK_APP=app.py \
    PYTHONUNBUFFERED=1 \
    GOOGLE_MAPS_API_KEY=your_api_key_here
```

---

## Step 4: Configure Startup Command

1. **Set Startup Script**
   - Azure Portal → App Service → Configuration
   - General settings → Startup Command
   ```bash
   bash startup.sh
   ```

2. **Alternative: Direct Gunicorn Command**
   ```bash
   gunicorn --bind=0.0.0.0:8000 --timeout=300 --workers=2 app:app
   ```

3. **Save and Restart**
   - Click "Save"
   - App will restart with new settings

---

## Step 5: Deploy Frontend (React)

### Option A: Serve from Backend (Simpler)

The GitHub Actions workflow already does this:
- Builds React app
- Copies to `backend/static/`
- Backend serves frontend at root URL

**Update backend/app.py** (add at the end):

```python
# Serve React frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path and os.path.exists(os.path.join('static', path)):
        return send_from_directory('static', path)
    return send_from_directory('static', 'index.html')
```

### Option B: Separate Frontend (Azure Static Web Apps)

1. **Create Static Web App**
   ```bash
   az staticwebapp create \
     --name excel-transformer-frontend \
     --resource-group excel-transformer-rg \
     --location southeastasia \
     --source https://github.com/yourusername/EL \
     --branch master \
     --app-location "/frontend" \
     --output-location "build"
   ```

2. **Update Frontend API URL**
   - Create `frontend/.env.production`
   ```
   REACT_APP_API_URL=https://excel-transformer.azurewebsites.net
   ```

---

## Step 6: Test Deployment

1. **Access Your App**
   ```
   Backend API: https://excel-transformer.azurewebsites.net
   Health Check: https://excel-transformer.azurewebsites.net/health
   Frontend: https://excel-transformer.azurewebsites.net/
   ```

2. **Check Logs** (if issues)
   - Azure Portal → App Service → Log stream
   - Or use CLI:
   ```bash
   az webapp log tail \
     --name excel-transformer \
     --resource-group excel-transformer-rg
   ```

3. **Test Upload**
   - Upload a test Excel file
   - Verify processing works
   - Check file download

---

## Step 7: Configure Custom Domain (Optional)

1. **Add Custom Domain**
   - Azure Portal → App Service → Custom domains
   - Click "Add custom domain"
   - Enter: `excel.yourcompany.com`

2. **Verify Domain Ownership**
   - Add DNS records as instructed by Azure
   - Wait for DNS propagation (5-60 minutes)

3. **Enable SSL**
   - Click "Add binding"
   - Select "SNI SSL" (free)
   - Azure creates free SSL certificate automatically

---

## Step 8: Monitor and Maintain

### Enable Application Insights (Monitoring)

```bash
# Create Application Insights
az monitor app-insights component create \
  --app excel-transformer-insights \
  --location southeastasia \
  --resource-group excel-transformer-rg

# Link to App Service
az webapp config appsettings set \
  --name excel-transformer \
  --resource-group excel-transformer-rg \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=<your-key>
```

### Set Up Alerts

1. **Azure Portal → Monitor → Alerts**
2. **Create alert rule**
   - Resource: Your App Service
   - Condition:
     - HTTP 5xx errors > 5 in 5 minutes
     - CPU Percentage > 80%
     - Memory Percentage > 90%
   - Action: Email your team

### Enable Auto-scaling (Optional)

```bash
az monitor autoscale create \
  --resource-group excel-transformer-rg \
  --resource excel-transformer \
  --resource-type Microsoft.Web/serverfarms \
  --name excel-autoscale \
  --min-count 1 \
  --max-count 3 \
  --count 1
```

---

## Automatic Deployment Workflow

Once set up, your deployment is fully automated:

```
1. Developer pushes code to GitHub (master branch)
   ↓
2. GitHub Actions automatically triggered
   ↓
3. Runs tests (if configured)
   ↓
4. Builds React frontend
   ↓
5. Installs Python dependencies
   ↓
6. Deploys to Azure App Service
   ↓
7. App restarts with new code
   ↓
8. Health check confirms deployment success
   ↓
9. ✅ New version live!
```

**Deployment time**: 3-5 minutes per push

---

## Cost Breakdown (Monthly Estimates)

### Basic Setup
```
App Service B1 (Basic):           ~$15/month
Application Insights:             ~$5/month
Storage (uploads/processed):      ~$1/month
Bandwidth (moderate usage):       ~$2/month
-------------------------------------------
Total:                            ~$23/month
```

### Production Setup
```
App Service S1 (Standard):        ~$70/month
Application Insights:             ~$10/month
Storage with backup:              ~$5/month
Azure Key Vault (secrets):        ~$1/month
Azure Monitor (alerts):           ~$2/month
-------------------------------------------
Total:                            ~$88/month
```

### Free Tier (Development Only)
```
App Service F1:                   $0/month
Limited features:
- 60 min CPU/day limit
- 1 GB storage
- No custom domains
- No SSL
- Not suitable for production
```

---

## Troubleshooting

### Issue: Deployment fails

**Solution 1: Check logs**
```bash
az webapp log tail --name excel-transformer --resource-group excel-transformer-rg
```

**Solution 2: Restart app**
```bash
az webapp restart --name excel-transformer --resource-group excel-transformer-rg
```

### Issue: "Application Error" page

**Check**: Startup command configured correctly
```bash
az webapp config show --name excel-transformer --resource-group excel-transformer-rg
```

### Issue: Files not persisting

**Solution**: Use Azure Storage Account
```bash
# Create storage account
az storage account create \
  --name exceltransformerstorage \
  --resource-group excel-transformer-rg \
  --location southeastasia \
  --sku Standard_LRS

# Mount to App Service
az webapp config storage-account add \
  --name excel-transformer \
  --resource-group excel-transformer-rg \
  --custom-id uploads \
  --storage-type AzureFiles \
  --account-name exceltransformerstorage \
  --share-name uploads \
  --mount-path /home/uploads
```

---

## Comparison: Render vs Azure

| Aspect | Render | Azure |
|--------|--------|-------|
| **Setup Complexity** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐ Moderate |
| **GitHub Integration** | ✅ Built-in | ✅ GitHub Actions |
| **Data Residency** | 🌍 Global | ✅ Singapore |
| **PDPA Compliance** | ⚠️ Limited | ✅ Enterprise-grade |
| **Cost** | $0 (free tier) | $15-70/month |
| **Scalability** | Limited | Excellent |
| **Support** | Community | Enterprise SLA |
| **Company Control** | ❌ No | ✅ Yes |

---

## Next Steps After Deployment

1. ✅ **Implement Auto-Deletion**
   - Add scheduled job to delete files after 24 hours
   - Use Azure Functions or background task

2. ✅ **Add Authentication**
   - Azure AD B2C for user login
   - Protect upload/download endpoints

3. ✅ **Set Up Monitoring**
   - Application Insights dashboards
   - Email alerts for errors

4. ✅ **Create Privacy Policy**
   - Document data handling
   - Add to frontend

5. ✅ **Backup Strategy**
   - Azure Backup for app configuration
   - Regular database backups (if added)

---

## Support Resources

- **Azure Documentation**: https://learn.microsoft.com/azure/app-service/
- **Pricing Calculator**: https://azure.microsoft.com/pricing/calculator/
- **Azure Support**: https://azure.microsoft.com/support/
- **Community Forum**: https://learn.microsoft.com/answers/

---

## Quick Command Reference

```bash
# Login
az login

# Check deployment status
az webapp show --name excel-transformer --resource-group excel-transformer-rg

# View logs
az webapp log tail --name excel-transformer --resource-group excel-transformer-rg

# Restart app
az webapp restart --name excel-transformer --resource-group excel-transformer-rg

# Update environment variable
az webapp config appsettings set --name excel-transformer --resource-group excel-transformer-rg --settings KEY=value

# Delete everything (cleanup)
az group delete --name excel-transformer-rg --yes
```

---

**Need help?** Contact your Azure administrator or refer to the Azure documentation linked above.
