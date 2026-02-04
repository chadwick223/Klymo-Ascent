import os
import django
import sys
import redis

# Setup Django environment
sys.path.append(r'c:\Users\satvi\OneDrive\Desktop\ascent\Veil')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Veil.settings')
django.setup()

from django.conf import settings

def clear_redis_data():
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )

    # Keys to clear
    keys_to_delete = []
    
    # 1. Queues
    keys_to_delete.extend(r.keys("queue:*"))
    
    # 2. Status flags
    keys_to_delete.extend(r.keys("in_queue:*"))
    keys_to_delete.extend(r.keys("cooldown:*"))
    keys_to_delete.extend(r.keys("chat:*")) # specific chat pubsub channels or keys
    
    # 3. Chat Session State in Redis (if any custom ones used)
    # The view used "in_chat:..." in LeaveChatView logic, assume we should clear that too if it exists
    keys_to_delete.extend(r.keys("in_chat:*"))

    if keys_to_delete:
        print(f"Deleting {len(keys_to_delete)} keys...")
        r.delete(*keys_to_delete)
        print("Redis matching data cleared.")
    else:
        print("No matching data found in Redis.")

if __name__ == "__main__":
    clear_redis_data()
