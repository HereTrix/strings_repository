from django.http import JsonResponse
from api.models import User
from api.serializers import UserSerializer, ProfileSerializer, LoginSerializer
from rest_framework import generics, permissions, status
from knox.models import AuthToken
import re


class SignInAPI(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data
            token = AuthToken.objects.create(user)
            print(token)
            return JsonResponse({
                "user": UserSerializer(user, context=self.get_serializer_context()).data,
                "token": token[1],
                "expired": token[0].expiry,
            })
        except Exception as e:
            return JsonResponse({
                "error": "Invalid credentials"
            }, status=status.HTTP_401_UNAUTHORIZED)


class ChangePasswordAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        password = request.data['password']
        new_password = request.data['new_password']
        if not user.check_password(password):
            return JsonResponse({
                'error': 'Password is invalid'
            }, status=status.HTTP_400_BAD_REQUEST)
        regex = "^(?=.*[A-Za-z])(?=.*\d).{8,}$"
        if not re.fullmatch(regex, new_password):
            return JsonResponse({
                'error': 'New password is invalid'
            }, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return JsonResponse({}, status=status.HTTP_200_OK)


class ProfileAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
        except User.DoesNotExist:
            return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(user)
        return JsonResponse(serializer.data)

    def post(self, request):
        email = request.data['email']
        first_name = request.data['first_name']
        last_name = request.data['last_name']
        try:
            user = request.user
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.save()
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(user)
        return JsonResponse(serializer.data)
