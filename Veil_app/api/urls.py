from django.urls import path
from .views import DeviceRegisterView,ProfileCreateView,ProfileStatusView,ManualGenderView,EnterMatchQueueView,LeaveMatchQueueView,GenderVerificationAiView

urlpatterns = [
    path('register-devices/',DeviceRegisterView.as_view(),name='register-devices'),
    path('create-profile/',ProfileCreateView.as_view(),name='create-profile'),
    path('status/<uuid:device_id>/', ProfileStatusView.as_view(), name='profile-status'),
    path('manual-verification/',ManualGenderView.as_view(),name='manual-verification'),
    path('enter-queue/',EnterMatchQueueView.as_view(),name='enter-queue'),
    path('leave-queue/',LeaveMatchQueueView.as_view(),name='leave-queue'),
    path('verify-gender-ai/',GenderVerificationAiView.as_view(),name='verify-gender-ai'),

]
