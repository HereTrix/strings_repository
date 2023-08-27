from django.http import JsonResponse
from api.models import UserProfile
from api.serializers import UserSerializer, ProfileSerializer, LoginSerializer
from rest_framework import generics, permissions, status
from knox.models import AuthToken


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


class ProfileAPI(generics.GenericAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return JsonResponse(status=status.HTTP_404_NOT_FOUND)

        serializer = ProfileSerializer(profile)
        return JsonResponse(serializer.data)
