from redis import Redis
from rq import Worker

from config import REDIS_URL, RQ_QUEUE_NAME


if __name__ == "__main__":
    redis_connection = Redis.from_url(REDIS_URL)
    worker = Worker([RQ_QUEUE_NAME], connection=redis_connection)
    worker.work()
