from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('auth/register/', views.RegisterView.as_view(), name='auth_register'),
    path('auth/login/', views.LoginView.as_view(), name='auth_login'),
    path('auth/me/', views.MeView.as_view(), name='auth_me'),
]
