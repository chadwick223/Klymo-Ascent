from django.db import models
import uuid
from django.utils import timezone
import datetime
# Create your models here.
# class Profile(models.Model):
#     pass
class Device(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False)
    fingerprint=models.CharField(max_length=255,unique=True)

    created_at=models.DateTimeField(auto_now_add=True)
    last_seen=models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Device {self.id}"

class Verificaton(models.Model):
    Gender_Choices=[
        ('male','Male'),
        ('female','Female'),
        ('other','Other')
    ]
    device=models.OneToOneField(Device,on_delete=models.CASCADE,related_name='verification')
    # have not done any ai classification yet
    # will do it later
    
    
    gender=models.CharField(max_length=10,choices=Gender_Choices)
    confidence = models.FloatField(null=True, blank=True)
    verified_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.device.id} - {self.gender}"

class Profile(models.Model):
    device=models.OneToOneField(Device,on_delete=models.CASCADE,related_name='profile')
    nickname=models.CharField(max_length=255)
    bio=models.CharField(max_length=150,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device.id} - {self.nickname}"

    
class Match_queue(models.Model):
    Gender_Filter=[
        ('Male','male'),
        ('Female','female'),
        ('Any','any')
    ]
    device=models.ForeignKey(Device,on_delete=models.CASCADE,related_name='match_queue')
    looking_for=models.CharField(max_length=10,choices=Gender_Filter,default='Any')
    joined_at=models.DateTimeField(auto_now_add=True,db_index=True)
    is_active=models.BooleanField(default=True)

    def __str__(self):
        return f"{self.device.id} in queue"

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False)
    user_a=models.ForeignKey(Device,on_delete=models.CASCADE,related_name='chat_as_a')
    user_b=models.ForeignKey(Device,on_delete=models.CASCADE,related_name='chat_as_b')
    started_at=models.DateTimeField(auto_now_add=True)
    ended_at=models.DateTimeField(null=True,blank=True)
    is_active=models.BooleanField(default=True)

    def __str__(self):
        return f"chat {self.id}"

class ChatMessage(models.Model):
    session=models.ForeignKey(ChatSession,on_delete=models.CASCADE)
    sender=models.ForeignKey(Device,on_delete=models.CASCADE)
    message=models.TextField()
    timestamp=models.DateTimeField(auto_now_add=True)

class Usage_limit(models.Model):
    device=models.OneToOneField(Device,on_delete=models.CASCADE,related_name='usage_limit')
    specific_gender_matches=models.PositiveIntegerField(default=0)
    last_reset = models.DateField(default=timezone.now)

    def reset_if_needed(self):
        last_reset_date = self.last_reset
        if isinstance(last_reset_date, datetime.datetime):
            last_reset_date = last_reset_date.date()
            
        if timezone.now().date() > last_reset_date:
            self.specific_gender_matches=0
            self.last_reset=timezone.now().date()
            self.save()

class Report(models.Model):
    reporter=models.ForeignKey(Device,on_delete=models.CASCADE,related_name='report_made')
    reported=models.ForeignKey(Device,on_delete=models.CASCADE,related_name='report_received')
    session=models.ForeignKey(ChatSession,on_delete=models.SET_NULL,null=True,blank=True)
    reason=models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    pass
    
    

