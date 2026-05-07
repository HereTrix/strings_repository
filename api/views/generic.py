from django.contrib.auth.models import User
from django_otp import user_has_device
from api.models.project import Invitation, ProjectRole
from api.models.users import PasskeyCredential
from api.serializers.users import UserSerializer, LoginSerializer
from api.throttles import LoginRateThrottle
from rest_framework.response import Response
from rest_framework import generics, permissions, status
from knox.models import AuthToken
import re


class SignInAPI(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data
            token = AuthToken.objects.create(user)

            if user_has_device(user, confirmed=True):
                return Response(
                    {'2fa_required': True, 'token': token[1]},
                    status=202,
                )

            return Response({
                "user": UserSerializer(user, context=self.get_serializer_context()).data,
                "token": token[1],
                "expired": token[0].expiry,
            })
        except Exception as e:
            return Response({
                "error": "Invalid credentials"
            }, status=status.HTTP_401_UNAUTHORIZED)


class ChangePasswordAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        password = request.data['password']
        new_password = request.data['new_password']
        if not user.check_password(password):
            return Response({
                'error': 'Password is invalid'
            }, status=status.HTTP_400_BAD_REQUEST)
        regex = r"^(?=.*[A-Za-z])(?=.*\d).{8,}$"
        if not re.fullmatch(regex, new_password):
            return Response({
                'error': 'New password is invalid'
            }, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({}, status=status.HTTP_200_OK)


class ProfileAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
        except User.DoesNotExist:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(user)
        data = serializer.data
        data['has_2fa'] = user_has_device(user, confirmed=True)
        passkeys = PasskeyCredential.objects.filter(
            user=user).values('id', 'name', 'created_at')
        data['passkeys'] = [
            {'id': p['id'], 'name': p['name'],
                'created_at': p['created_at'].isoformat()}
            for p in passkeys
        ]
        return Response(data)

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
            return Response({
                'error': e
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = UserSerializer(user)
        return Response(serializer.data)


class ActivateProjectAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            code = request.data['code']

            invite = Invitation.objects.get(
                code=code)

            existing_role = [
                role for role in invite.project.roles.all() if role.user == user]

            ids = [role.user.id for role in invite.project.roles.all()]

            if existing_role:
                return Response({
                    'error': 'Already participating in project'
                })

            role = ProjectRole()
            role.user = user
            role.project = invite.project
            role.role = invite.role
            role.save()

            invite.delete()

            return Response({})
        except Invitation.DoesNotExist:
            return Response({
                'error': 'Wrong activation code'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)


class SignUpAPI(generics.GenericAPIView):

    def post(self, request):

        login = request.data.get('login')
        if not login:
            return Response({
                'error': 'Login should not be empty'
            }, status=status.HTTP_400_BAD_REQUEST)

        password = request.data.get('password')
        regex = r"^(?=.*[A-Za-z])(?=.*\d).{8,}$"
        if not re.fullmatch(regex, password):
            return Response({
                'error': 'Password is not strong enough'
            }, status=status.HTTP_400_BAD_REQUEST)

        code = request.data.get('code')
        if not code:
            return Response({
                'error': 'Invitation code should not be empty'
            }, status=status.HTTP_400_BAD_REQUEST)

        name = request.data.get('name')
        if not name:
            return Response({
                'error': 'Please provide name'
            }, status=status.HTTP_400_BAD_REQUEST)

        surname = request.data.get('surname')
        if not surname:
            return Response({
                'error': 'Please provide last name'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            invitation = Invitation.objects.get(code=code)
        except Invitation.DoesNotExist:
            return Response({
                'error': 'Invitation code is invalid'
            })

        try:
            user = User.objects.get(username=login)
            return Response({
                'error': 'Please, activate code on your profile page'
            })
        except User.DoesNotExist:
            user = User()
            user.username = login
            user.first_name = name
            user.last_name = surname
            user.set_password(password)
            user.save()

        role = ProjectRole()
        role.role = invitation.role
        role.user = user
        role.project = invitation.project
        role.save()

        invitation.delete()

        return Response({})
