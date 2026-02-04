from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from .serializers import DeviceSerializer,ProfileSerializer,GenderVerificationManualSerializer,MatchRequestSerializer,GenderSerializer,ReportSerializer
from Veil_app.models import Device,Verificaton,Profile,Match_queue,ChatSession,ChatMessage,Usage_limit,Report
from django.db import models
from Veil_app.services.matchmaking import MatchmakingService
from Veil_app.Ai_verification.verification import verify_gender_ai
from rest_framework.parsers import MultiPartParser, FormParser
# import asyncio
# from typing import AsyncGenerator
from Veil_app.redis import redis_client
from django.http import StreamingHttpResponse
import time
import json
from django.utils import timezone

from django.views import View
from django.http import JsonResponse, StreamingHttpResponse
import redis.asyncio as aioredis
from django.conf import settings
import asyncio

class ChatStreamView(View):

    async def get(self,request,chat_id):
        device_id=request.GET.get('device_id')

        if not device_id:
            return JsonResponse({"error": "Device ID missing"},status=400)
        
        # Async DB access
        try:
            chat_session = await ChatSession.objects.aget(id=chat_id, is_active=True)
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Chat session not found"},status=404)
        
        # Verify Auth (User IDs are UUIDs, convert to str)
        if str(device_id) not in [str(chat_session.user_a_id), str(chat_session.user_b_id)]:
             return JsonResponse({"error": "Unauthorized"},status=401)

        async def event_stream():
            # Create local async redis connection
            r = aioredis.Redis(
                host=settings.REDIS_HOST, 
                port=settings.REDIS_PORT, 
                db=settings.REDIS_DB, 
                decode_responses=True
            )
            pubsub = r.pubsub()
            await pubsub.subscribe(f"chat:{chat_id}")
            
            try:
                # Send initial ping
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                print(f"DEBUG: Async Subscribed to chat:{chat_id}")

                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        print(f"DEBUG: Async Redis Message: {message['data']}")
                        yield f"data: {message['data']}\n\n"
            except Exception as e:
                print(f"ERROR: ChatStreamView crashed: {e}")
                raise e
            finally:
                await r.close()

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class SendMessageView(APIView):
    
    def post(self,request):
        chat_id=request.data.get('chat_id')
        device_id=request.data.get('device_id')
        message=request.data.get('message')

        if not chat_id or not device_id or not message:
            return Response({"error": "Missing required parameters"},status=status.HTTP_400_BAD_REQUEST)
            
        chat=get_object_or_404(ChatSession,id=chat_id,is_active=True)
        sender = get_object_or_404(Device, id=device_id)
        if str(device_id) not in [
            str(chat.user_a.id),
            str(chat.user_b.id)
        ]:
            return Response({"error": "Unauthorized"},status=status.HTTP_401_UNAUTHORIZED)
        ChatMessage.objects.create(
            session=chat,
            sender=sender,
            message=message

        )
        payload={
            "sender":device_id,
            "message":message,
            "timestamp":time.time()
        }
        redis_client.publish(
            f"chat:{chat_id}",
            json.dumps(payload)
        )
        return Response({"message": "Message sent successfully"}, status=status.HTTP_200_OK)
    

class DeviceRegisterView(APIView):

    def post(self, request):
        serializer = DeviceSerializer(data=request.data)
        if serializer.is_valid():
            fingerprint=serializer.validated_data['fingerprint']
            print(f"DEBUG: Registering fingerprint: {fingerprint}")
            device,created=Device.objects.get_or_create(fingerprint=fingerprint)
            print(f"DEBUG: Device {device.id} Created: {created}. Has Profile: {hasattr(device, 'profile')}")

            return Response({
                'message':'Welcome to Veil',
                'device_id':device.id,
                'fingerprint':device.fingerprint,
                'is_new_user':created
            },status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

class LeaveChatView(APIView):

    def post(self, request):
        chat_id = request.data.get("chat_id")
        device_id = request.data.get("device_id")

        if not chat_id or not device_id:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        chat = get_object_or_404(ChatSession, id=chat_id, is_active=True)

        if str(device_id) not in [str(chat.user_a.id), str(chat.user_b.id)]:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        
        chat.is_active = False
        chat.ended_at = timezone.now()
        chat.save(update_fields=["is_active","ended_at"])

        redis_client.delete(f"in_chat:{chat.user_a_id}")
        redis_client.delete(f"in_chat:{chat.user_b_id}")


        redis_client.publish(
            f"chat:{chat_id}",
            json.dumps({
                "type": "chat_ended",
                "ended_by": device_id,
                "timestamp": time.time()
            })
        )

        return Response({"message": "Chat ended"}, status=status.HTTP_200_OK)


class ReportView(APIView):

    def post(self, request):
        serializer = ReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_id = serializer.validated_data["device_id"]
        session_id = serializer.validated_data.get("session_id")

        reporter = get_object_or_404(Device, id=device_id)

        session = None
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id)

            if reporter.id not in [
                session.user_a_id,
                session.user_b_id
            ]:
                return Response(
                    {"error": "You are not part of this chat session"},
                    status=status.HTTP_403_FORBIDDEN
                )

        report = Report.objects.create(
            reporter=reporter,
            session=session,
            reported=serializer.validated_data["reported"],
            reason=serializer.validated_data["reason"]
        )

        return Response(
            {
                "message": "Report submitted successfully",
                "report_id": report.id
            },
            status=status.HTTP_201_CREATED
        )


class ProfileCreateView(APIView):

    def post(self,request):
        device_id=request.data.get('device_id')
        try:
            device = Device.objects.get(id=device_id)
        except (Device.DoesNotExist, ValueError):
            return Response({"error": "Invalid Device ID"}, status=status.HTTP_404_NOT_FOUND)
        if hasattr(device,'profile'):
            return Response({"error": "Profile already exists"}, status=status.HTTP_400_BAD_REQUEST)
        serializer=ProfileSerializer(data=request.data)
        if serializer.is_valid():
            profile=serializer.save(device=device)
            return Response({"message": "Profile created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileStatusView(APIView):
    def get(self,request,device_id):

        try:
            device = Device.objects.get(id=device_id)
        except (Device.DoesNotExist, ValueError):
            return Response({
                "exists":False,
                "message":"Device not found"
            },status=status.HTTP_404_NOT_FOUND)
        has_profile = hasattr(device, 'profile')
        is_verified = hasattr(device, 'verification')

        next_step="complete_onboarding"
        if not has_profile:
            next_step="create_profile"
        elif not is_verified:
            next_step="verify_gender"
        else:
            next_step="start_matching"

        return Response({
            "exists": True,
            "has_profile": has_profile,
            "is_verified": is_verified,
            "next_step": next_step,
            "profile_name": device.profile.nickname if has_profile else None
        }, status=status.HTTP_200_OK)

        
        # if hasattr(device,'profile'):
        #     return Response({"error": "Profile already exists"}, status=status.HTTP_400_BAD_REQUEST)


class ManualGenderView(APIView):

    def post(self,request):
        
        serializer=GenderVerificationManualSerializer(data=request.data)

        if serializer.is_valid():
            
            device_id=serializer.validated_data['device_id']
            selected_gender=serializer.validated_data['gender']
            
            device=get_object_or_404(Device,id=device_id)
            
            verification,create=Verificaton.objects.update_or_create(
                device=device,
                defaults={'gender':selected_gender}
            )
            return Response({
                "message": "Gender set successfully (Mock Verification)",
                "device_id": device.id,
                "gender": verification.gender,
                "is_verified": True # We mark them as verified manually
            },status=status.HTTP_200_OK)
        
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        

class EnterMatchQueueView(APIView):

    def post(self,request):
        serializer=MatchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        device_id=request.data.get('device_id')
        if not device_id:
            return Response(
                {"error": "Device ID missing"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            result=MatchmakingService.enter_queue(device_id=device_id, preference=serializer.validated_data['preference'])
        
            return Response(result,status=status.HTTP_200_OK)
        
        except PermissionError as e:
            return Response({"error": str(e)},status=status.HTTP_403_FORBIDDEN)

        except ValueError as e:
            return Response({"error": str(e)},status=status.HTTP_400_BAD_REQUEST)
        


class LeaveMatchQueueView(APIView):

    def post(self, request):
        device_id = request.data.get("device_id")

        if not device_id:
            return Response(
                {"error": "Device ID missing"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            MatchmakingService.leave_queue(device_id)
            return Response(
                {"message": "Left queue. Cooldown started."},
                status=status.HTTP_200_OK
            )

        except PermissionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )

        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class GenderVerificationAiView(APIView):

    parser_classes = [MultiPartParser, FormParser]

    def post(self,request):
        serializer=GenderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        device_id=serializer.validated_data['device_id']
        image=serializer.validated_data['image']


        try:
            device=Device.objects.get(id=device_id)
        except (Device.DoesNotExist, ValueError):
            return Response({"error": "Invalid Device ID"}, status=status.HTTP_404_NOT_FOUND)
        
        result = verify_gender_ai(image.read())

        if result["status"] != "success":
            return Response(
                {
                    "status": "failed",
                    "reason": result.get("message", "Verification failed")
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        verification, _ = Verificaton.objects.update_or_create(
            device=device,
            defaults={
                "gender": result["gender"],
                "confidence": result["confidence"],
            }
        )

        return Response({
            "status": "success",
            "gender": verification.gender,
            "confidence": verification.confidence,
        })




        #     return Response({"error": str(e)},status=status.HTTP_400_BAD_REQUEST)

class MatchStatusView(APIView):
    def get(self, request, device_id):
        try:
            device = Device.objects.get(id=device_id)
        except (Device.DoesNotExist, ValueError):
             return Response({"error": "Invalid Device ID"}, status=status.HTTP_404_NOT_FOUND)

        # 1. Check if in active chat
        active_chat = ChatSession.objects.filter(
            models.Q(user_a=device) | models.Q(user_b=device),
            is_active=True
        ).first()

        if active_chat:
            return Response({
                "status": "matched",
                "chat_id": active_chat.id,
                "partner_id": active_chat.user_b.id if active_chat.user_a == device else active_chat.user_a.id
            })

        # 2. Check if in queue (using Redis)
        # The MatchmakingService sets "in_queue:{device.id}"
        if redis_client.exists(f"in_queue:{device.id}"):
            return Response({"status": "in_queue"})

        # 3. Check cooldown
        if redis_client.exists(f"cooldown:{device.id}"):
             ttl = redis_client.ttl(f"cooldown:{device.id}")
             return Response({"status": "cooldown", "remaining_seconds": ttl})

        return Response({"status": "idle"})

