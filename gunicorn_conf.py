# gunicorn_conf.py

# Bind to all interfaces on port 5000
bind = "0.0.0.0:5000"

# Only 1 worker process is probably enough for light usage
workers = 1

# Use sync worker class (default) for simple, I/O-light apps
worker_class = "sync"

# Set a slightly generous timeout
timeout = 60

# Optional: log level
loglevel = "info"
