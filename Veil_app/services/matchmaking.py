
import time
import json
from django.conf import settings
from Veil_app.redis import redis_client
from Veil_app.models import Device,Verificaton,Profile,Match_queue,ChatSession,ChatMessage,Usage_limit,Report


QUEUE_KEYS = {
    "male": "queue:male",
    "female": "queue:female",
    "any": "queue:any",
}

cooldown_seconds=20
DAILY_LIMIT = 5


class MatchmakingService:

    @classmethod
    def enter_queue(cls, device_id, preference):
        device = cls._get_valid_device(device_id)

        cls._ensure_not_in_cooldown(device_id)

        cls._ensure_not_in_queue(device_id)

        cls._check_usage_limit(device, preference)



        match = cls._try_find_match(device, preference)


        if match:
            chat=ChatSession.objects.create(
                user_a=device,
                user_b_id=match["device_id"],
                is_active=True
            )
            cls._clear_queue_flag(device_id)
            
            cls._increment_usage(device.id, preference)
            cls._increment_usage(match["device_id"], match["preference"])
            
            return {
                "matched": True,
                "chat_id":str(chat.id),
                "partner_device_id": match["device_id"],
                "message":"Match found"
            }

        # No match → enqueue
        cls._enqueue(device, preference)

        return {
            "matched": False,
            "message":"Joined queue successfully"
        }

    @classmethod
    def leave_queue(cls, device_id):
        """
        Remove user from queue and apply cooldown.
        """
        cls._remove_from_queue(device_id)
        cls._apply_cooldown(device_id)

    @classmethod
    def _try_find_match(cls, device, preference):

        candidate_queues = cls._get_candidate_queues(
            device.verification.gender, preference
        )
        
        for queue_key in candidate_queues:
            # Loop until we find a match or run out of candidates in this queue
            # We use a loop so we can discard "ghost" users (those who left queue)
            while True:
                raw = redis_client.lpop(queue_key)

                if not raw:
                    break # Queue empty, move to next queue
                
                candidate = json.loads(raw)
                
                # Check 1: Is this ME? (Stale entry from my previous join?)
                if candidate["device_id"] == str(device.id):
                    print(f"DEBUG: Dropping self from queue {candidate['device_id']}")
                    continue # DROP IT (don't push back)

                # Check 2: Is the candidate actually ONLINE? (Has in_queue flag?)
                if not redis_client.exists(f"in_queue:{candidate['device_id']}"):
                    print(f"DEBUG: Dropping ghost user {candidate['device_id']}")
                    continue # DROP IT (they left the queue)

                # Check 3: Compatibility
                if cls._is_compatible(
                    device_gender=device.verification.gender,
                    device_preference=preference,
                    candidate=candidate
                ):
                    cls._clear_queue_flag(candidate["device_id"])
                    return candidate
                
                # Valid user, but not compatible (e.g. preference mismatch)
                # This puts them back at the TAIL. Ideally we'd put at HEAD but Redis lists are simple.
                # For a true queue we might want rpoplpush or similar, but for now rpush is safe enough 
                # to keep them in circulation, though they lose their spot. 
                # To preserve order we would need `lpush` if we popped from left, but if we assume
                # the queue is FIFO, we just skipped them. 
                # Actually, if they are incompatible with US, they might be compatible with someone else.
                # Putting them back is correct.
                redis_client.rpush(queue_key, raw)
                
                # Break the inner while loop to avoid infinite spinning if everyone is incompatible
                # We checked one valid candidate from this queue, let's move to next queue or 
                # stop to avoid consuming the whole CPU in one request if the queue is huge.
                # BUT: If we break here, we only check ONE valid person per queue per request.
                # That might be slow. Let's try checking a few or just continue.
                # For this simple implementation, let's break to be safe and fair.
                break 
        return None

    @classmethod
    def _enqueue(cls, device, preference):
        payload = {
            "device_id": str(device.id),
            "gender": device.verification.gender,
            "preference": preference,
            "joined_at": int(time.time()),
        }

        queue_key = QUEUE_KEYS[preference]
        redis_client.rpush(queue_key, json.dumps(payload))
        redis_client.set(f"in_queue:{device.id}", "1")

    @staticmethod
    def _get_candidate_queues(device_gender, preference):
        
        if preference == "any":
            return [
                QUEUE_KEYS["male"],
                QUEUE_KEYS["female"],
                QUEUE_KEYS["any"],
            ]

        return [
            QUEUE_KEYS[preference],
            QUEUE_KEYS["any"],
        ]
    
    @staticmethod
    def _is_compatible(device_gender,device_preference,candidate):

        def accepts(pref, gender):

            return pref == "any" or pref == gender
        return (
            accepts(candidate["preference"], device_gender)
            and accepts(device_preference, candidate["gender"])
        )

    
    @staticmethod
    def _get_valid_device(device_id):
        device = Device.objects.filter(id=device_id).first()
        if not device:
            raise ValueError("Invalid device")
        if not hasattr(device, "verification"):
            raise PermissionError("Device not verified")
        return device

    @staticmethod
    def _ensure_not_in_queue(device_id):
        if redis_client.exists(f"in_queue:{device_id}"):
            raise PermissionError("Already in queue")

    @staticmethod
    def _ensure_not_in_cooldown(device_id):
        if redis_client.exists(f"cooldown:{device_id}"):
            raise PermissionError("Already in cooldown")

    @staticmethod

    def _remove_from_queue(device_id):
        # Simple version (v1): just clear flag
        redis_client.delete(f"in_queue:{device_id}")


    @staticmethod

    def _apply_cooldown(device_id):
        redis_client.setex(
            f"cooldown:{device_id}",
            cooldown_seconds,
            "1"
        )

    @staticmethod
    def _clear_queue_flag(device_id):
        redis_client.delete(f"in_queue:{device_id}")

   
        
        
    

    @staticmethod
    def _check_usage_limit(device, preference):
        if preference == 'any':
            return

        usage, _ = Usage_limit.objects.get_or_create(device=device)
        usage.reset_if_needed()

        if usage.specific_gender_matches >= DAILY_LIMIT:
            raise PermissionError('Daily limit for specific gender matches reached')

    @staticmethod
    def _increment_usage(device_id, preference):
        if preference == 'any':
            return

        usage, _ = Usage_limit.objects.get_or_create(device_id=device_id)
        usage.reset_if_needed()
        usage.specific_gender_matches += 1
        usage.save()


