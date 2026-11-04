from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema
from .serializers import (
    RegisterSerializer, UserSerializer, LogoutSerializer,
)


class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: dict}, summary="Health check")
    def get(self, request):
        return Response({"status": "ok", "service": "social-publisher"})


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    @extend_schema(request=LogoutSerializer)
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Logged out."}, status=status.HTTP_205_RESET_CONTENT)