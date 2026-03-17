"""
Gunicorn production configuration.
Run with: gunicorn -c gunicorn.conf.py run:app
"""
import os
import multiprocessing

# Bind address
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"

# Workers: 2–4x CPU cores handles 100s of concurrent requests
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
threads = 2                  # Threads per worker
timeout = 30                 # Kill stuck workers after 30s
keepalive = 5                # Keep-alive connections
max_requests = 1000          # Restart workers after 1000 requests (memory leak guard)
max_requests_jitter = 200    # Randomize restart to avoid thundering herd

# Logging
accesslog = '-'              # stdout
errorlog  = '-'              # stderr
loglevel  = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs'

# Security
forwarded_allow_ips = '*'   # Trust X-Forwarded-For from proxy (set to proxy IP in prod)
