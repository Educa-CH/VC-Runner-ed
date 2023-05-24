bind = "register-ed.educa.ch:443"
certfile = "/usr/local/share/certs/educa.ch/fullchain.pem"
keyfile = "/usr/local/share/certs/educa.ch/privkey.pem"
workers = 2  # Number of worker processes to spawn
threads = 4  # Number of threads per worker
worker_class = "gthread"  # Worker class to use
accesslog = 'logs/access'
errorlog = 'logs/error'
capture_output = True
timeout = 120

#gunicorn app:app -c gunicorn.conf.py --log-level=debug