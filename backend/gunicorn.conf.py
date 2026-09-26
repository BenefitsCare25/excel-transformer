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

# No request-count recycling: the worker hosts the hospital OCR queue thread, and a browser polling
# progress every 3 s would otherwise restart it mid-document. Page checkpoints cover other restarts.
max_requests = 0

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


def post_worker_init(worker):
    from hospital_services.jobs import start
    start(worker.wsgi.config['HOSPITAL_OUTPUT_DIR'], worker.log)

# SSL
keyfile = None
certfile = None
