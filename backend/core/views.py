from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer, UserSerializer


def health_check(request):
    db_ok = False
    redis_ok = False

    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        pass

    try:
        cache.set("health_check", "ok", timeout=5)
        redis_ok = cache.get("health_check") == "ok"
    except Exception:
        pass

    status_str = "ok" if db_ok and redis_ok else "degraded"
    return JsonResponse(
        {"status": status_str, "db": "ok" if db_ok else "error", "redis": "ok" if redis_ok else "error"},
        status=200 if status_str == "ok" else 503,
    )


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {'token': token.key, 'user': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    def post(self, request):
        email = (request.data.get('email') or '').strip()
        password = request.data.get('password') or ''
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'error': 'אימייל או סיסמה שגויים'}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user).data})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def delete(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoogleCallbackView(APIView):
    """
    Called by PSA after Google OAuth completes (via social_django middleware).
    Reads the DRF token created in the pipeline and redirects the browser
    to the frontend with ?token=<token> so the SPA can store it.
    """

    def get(self, request):
        from django.conf import settings
        from django.shortcuts import redirect
        from rest_framework.authtoken.models import Token

        if not request.user.is_authenticated:
            return redirect(f"{settings.FRONTEND_URL}/login?error=auth_failed")

        token, _ = Token.objects.get_or_create(user=request.user)
        user = request.user
        params = (
            f"token={token.key}"
            f"&email={user.email}"
            f"&first_name={user.first_name}"
            f"&last_name={user.last_name}"
        )
        return redirect(f"{settings.FRONTEND_URL}/auth/callback?{params}")
