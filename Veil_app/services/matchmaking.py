
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


class MatchmakingService:

    @classmethod
    def enter_queue(cls, device_id, preference):
        device = cls._get_valid_device(device_id)

        cls._ensure_not_in_cooldown(device_id)

        cls._ensure_not_in_queue(device_id)



        match = cls._try_find_match(device, preference)


        if match:
            return {
                "matched": True,
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

            raw = redis_client.lpop(queue_key)



            if not raw:
                continue
            candidate = json.loads(raw)
            if candidate["device_id"] == str(device.id):
                redis_client.rpush(queue_key, raw)
                continue
            if cls._is_compatible(
                device_gender=device.verification.gender,
                device_preference=preference,
                candidate=candidate
            ):
                cls._clear_queue_flag(candidate["device_id"])
                return candidate
            redis_client.rpush(queue_key, raw)
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

        
    
