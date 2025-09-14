import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
backlog = 2048

# Worker processes - optimized for free tier
workers = 1
worker_class = 'sync'
worker_connections = 500  # Reduced for memory efficiency
timeout = 300
keepalive = 2

# Restart workers more frequently to prevent memory leaks on free tier
max_requests = 500  # Reduced from 1000
max_requests_jitter = 25  # Reduced from 50

# Memory optimization
preload_app = True
worker_tmp_dir = '/dev/shm'  # Use RAM disk for temporary files

# Logging
loglevel = 'info'
accesslog = '-'
errorlog = '-'

# Process naming
proc_name = 'excel-transformer'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None