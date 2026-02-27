import os

from redis import Redis
from rq import Worker, Queue

redis_conn = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))

if __name__ == "__main__":
    q = Queue("profiling", connection=redis_conn)
    w = Worker([q], connection=redis_conn)
    w.work()
