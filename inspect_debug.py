import os
import django
import sys
import redis
import json

# Setup Django environment
sys.path.append(r'c:\Users\satvi\OneDrive\Desktop\ascent\Veil')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Veil.settings')
django.setup()

from django.conf import settings
from Veil_app.models import ChatSession, Device

def inspect_state():
    print("\n========== INSPECTION START ==========")
    
    # 1. DB Active Sessions
    print("\n--- ACTIVE CHAT SESSIONS (DB) ---")
    sessions = ChatSession.objects.filter(is_active=True)
    if not sessions.exists():
        print("No active chat sessions found.")
    for s in sessions:
        print(f"Chat ID: {s.id}")
        u1 = s.user_a
        u2 = s.user_b
        print(f"   User A: {u1.id} ({u1.fingerprint})")
        print(f"   User B: {u2.id} ({u2.fingerprint})")
        print(f"   Started: {s.started_at}")

    # 2. Redis Queues
    print("\n--- REDIS QUEUE STATUS ---")
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        queues = ["queue:male", "queue:female", "queue:any"]
        for q in queues:
            length = r.llen(q)
            print(f"Queue '{q}': {length} users")
            if length > 0:
                items = r.lrange(q, 0, -1)
                for i, raw in enumerate(items):
                    data = json.loads(raw)
                    print(f"   [{i}] Device ID: {data.get('device_id')} | Pref: {data.get('preference')}")
    except Exception as e:
        print(f"Redis Error: {e}")

    print("\n========== INSPECTION END ==========")

if __name__ == "__main__":
    inspect_state()
