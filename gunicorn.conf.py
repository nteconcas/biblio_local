import multiprocessing
import os


bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = int(
    os.environ.get(
        'GUNICORN_WORKERS',
        str(max(multiprocessing.cpu_count() * 2 + 1, 2))
    )
)
threads = int(os.environ.get('GUNICORN_THREADS', '2'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '5'))
accesslog = '-'
errorlog = '-'
