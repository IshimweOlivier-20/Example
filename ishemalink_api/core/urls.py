"""
URL configuration for core app (authentication and user management).
"""
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-nid/', views.verify_nid, name='verify-nid'),
    path('users/me/', views.user_profile, name='user-profile'),
    path('users/agents/onboard/', views.agent_onboarding, name='agent-onboard'),
]
