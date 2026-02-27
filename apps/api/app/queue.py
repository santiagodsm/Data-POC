import os

from redis import Redis
from rq import Queue

_redis = Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))

profiling_queue = Queue("profiling", connection=_redis)
