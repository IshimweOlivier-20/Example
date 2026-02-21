import multiprocessing

bind = "0.0.0.0:8000"
workers = max(multiprocessing.cpu_count() * 2 + 1, 3)
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
accesslog = "-"
errorlog = "-"
