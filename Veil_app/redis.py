from django.conf import settings    



import redis

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

# redis_client = redis.Redis(host='localhost', port=6379, db=0,decode_responses=True)