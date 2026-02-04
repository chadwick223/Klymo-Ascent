from django.urls import path
from .views import DeviceRegisterView,ProfileCreateView,ProfileStatusView,ManualGenderView,EnterMatchQueueView,LeaveMatchQueueView,GenderVerificationAiView,ChatStreamView,SendMessageView,MatchStatusView,LeaveChatView,ReportView

urlpatterns = [
    path('register-devices/',DeviceRegisterView.as_view(),name='register-devices'),
    path('create-profile/',ProfileCreateView.as_view(),name='create-profile'),
    path('status/<uuid:device_id>/', ProfileStatusView.as_view(), name='profile-status'),
    path('manual-verification/',ManualGenderView.as_view(),name='manual-verification'),
    path('enter-queue/',EnterMatchQueueView.as_view(),name='enter-queue'),
    path('leave-queue/',LeaveMatchQueueView.as_view(),name='leave-queue'),
    path('verify-gender-ai/',GenderVerificationAiView.as_view(),name='verify-gender-ai'),
    path('chat/<uuid:chat_id>/stream/', ChatStreamView.as_view(), name='chat-stream'),
    path('chat/send/', SendMessageView.as_view(), name='send-message'),
    path('match-status/<uuid:device_id>/', MatchStatusView.as_view(), name='match-status'),
    path('chat/leave/', LeaveChatView.as_view(), name='leave-chat'),
    path('report/', ReportView.as_view(), name='report-user'),

]
