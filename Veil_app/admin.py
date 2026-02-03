from django.contrib import admin
from .models import Device,Verificaton,Profile,Match_queue,ChatSession,ChatMessage,Usage_limit,Report
# Register your models here.

admin.site.register(Device)
admin.site.register(Verificaton)
admin.site.register(Profile)
admin.site.register(Match_queue)
admin.site.register(ChatSession)
admin.site.register(ChatMessage)
admin.site.register(Usage_limit)
admin.site.register(Report)
