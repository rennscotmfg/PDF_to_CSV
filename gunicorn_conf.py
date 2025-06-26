# gunicorn_conf.py

bind = "0.0.0.0:443"

workers = 2

threads = 4

worker_class = "gthread"

worker_tmp_dir = "/dev/shm"

certfile = "cert.pem"
keyfile = "key.pem"
