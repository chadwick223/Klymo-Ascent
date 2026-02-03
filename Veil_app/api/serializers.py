from rest_framework import serializers
from Veil_app.models import Device,Verificaton,Profile,Match_queue,ChatSession,ChatMessage,Usage_limit,Report
import uuid


class DeviceSerializer(serializers.Serializer):

    fingerprint=serializers.CharField(max_length=255,required=True)

    def validate_fingerprint(self, value):
        if len(value.strip())<10:
            raise serializers.ValidationError("Fingerprint is too short")
        return value


class ProfileSerializer(serializers.Serializer):

    nickname=serializers.CharField(max_length=255)
    bio=serializers.CharField(max_length=150,required=False,allow_blank=True)

    def create(self,validated_data):
        return Profile.objects.create(**validated_data)

    def validate_name(self,value):

        if "admin" in value.lower():
            raise serializers.ValidationError("Invalid nickname")
        return value.strip()

class GenderSerializer(serializers.Serializer):
    # still no ai to verify if its a male or a female
    device_id=serializers.UUIDField()
    image=serializers.ImageField(required=True)

    def validate_image(self,image):
        if image.size>2*1024*1024:
            raise serializers.ValidationError("Image size should be less than 10MB")
        return image

class GenderVerificationManualSerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    gender = serializers.ChoiceField(choices=["male", "female","other"])

        

class MatchRequestSerializer(serializers.Serializer):
    preference = serializers.ChoiceField(
        choices=["male", "female", "any"]
    )

class ReportSerializer(serializers.ModelSerializer):

    class Meta:
        model=Report
        fields=['reported','reason']

    def validate(self,value):
        if len(value)<5:
            raise serializers.ValidationError("Too Short")
        return value

class UsageStatusSerializer(serializers.Serializer):
    specific_gender_matches = serializers.IntegerField()
    remaining_today = serializers.IntegerField()
    
    

    