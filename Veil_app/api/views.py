from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from .serializers import DeviceSerializer,ProfileSerializer,GenderVerificationManualSerializer,MatchRequestSerializer,GenderSerializer
from Veil_app.models import Device,Verificaton,Profile,Match_queue,ChatSession,ChatMessage,Usage_limit,Report
from Veil_app.services.matchmaking import MatchmakingService
from Veil_app.Ai_verification.verification import verify_gender_ai
from rest_framework.parsers import MultiPartParser, FormParser
class DeviceRegisterView(APIView):

    def post(self, request):
        serializer = DeviceSerializer(data=request.data)
        if serializer.is_valid():
            fingerprint=serializer.validated_data['fingerprint']
            device,created=Device.objects.get_or_create(fingerprint=fingerprint)

            return Response({
                'message':'Welcome to Veil',
                'device_id':device.id,
                'fingerprint':device.fingerprint,
                'is_new_user':created
            },status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

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
        
        MatchmakingService.enter_queue(device_id, preference)
        return Response({
                "message": "Joined queue successfully",
                "device_id": device_id,
                "preference": preference
            },status=status.HTTP_200_OK)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

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




        # if not device_id:
        #     return Response(
        #         {"error": "Device ID missing"},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # try:
        #     result=verify_gender_ai(device_id=device_id)
        #     return Response(result,status=status.HTTP_200_OK)
        # except PermissionError as e:
        #     return Response({"error": str(e)},status=status.HTTP_403_FORBIDDEN)
        # except ValueError as e:
        #     return Response({"error": str(e)},status=status.HTTP_400_BAD_REQUEST)
