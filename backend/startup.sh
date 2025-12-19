#!/bin/bash
# Azure App Service startup script
# This script runs when your app starts on Azure

echo "==================================="
echo "Starting Excel Transformer Backend"
echo "==================================="

# Create required directories
mkdir -p uploads processed

# Set permissions
chmod 755 uploads processed

# Environment info
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Environment: $FLASK_ENV"

# Start Gunicorn with Azure-optimized settings
echo "Starting Gunicorn..."
gunicorn --bind=0.0.0.0:8000 \
         --workers=2 \
         --worker-class=sync \
         --timeout=300 \
         --access-logfile=- \
         --error-logfile=- \
         --log-level=info \
         app:app
