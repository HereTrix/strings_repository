from datetime import datetime
import random
import string
from django.http import JsonResponse
from rest_framework import generics, permissions, status

from api.models import Invitation, Project, ProjectAccessToken, ProjectRole
from api.serializers import ProjectAccessTokenSerializer, ProjectParticipantsSerializer


class RolesAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            user = request.user

            role = ProjectRole.objects.filter(
                project__pk=pk,
                user=user,
            ).first()

            if role.role == ProjectRole.Role.admin:
                data = ProjectRole.common_roles
            elif role.role == ProjectRole.Role.owner:
                data = [role.value for role in ProjectRole.Role]
            elif role.role == ProjectRole.Role.editor:
                data = [ProjectRole.Role.translator, ProjectRole.Role.editor]
            else:
                return JsonResponse({
                    'error': 'User is not allowed to set roles'
                }, status=status.HTTP_403_FORBIDDEN)
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)


class ProjectParticipantsAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            user = request.user
            project = Project.objects.get(
                pk=pk,
                roles__user=user,
                roles__role__in=ProjectRole.change_participants_roles
            )

            return JsonResponse(ProjectParticipantsSerializer.serialize(project.roles.all(), user), safe=False)
        except Project.DoesNotExist:
            return JsonResponse({
                'error': 'Participants can not be viewed'
            }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, pk):
        try:
            user_id = request.data['user_id']
            new_role = request.data['role']
            user = request.user
            project = Project.objects.get(
                pk=pk,
                roles__user=user,
                roles__role__in=ProjectRole.change_participants_roles
            )

            all_roles = project.roles.all()

            user_role = [
                role for role in all_roles if role.user.id == user_id][0]
            user_role.role = new_role
            user_role.save()

            return JsonResponse(ProjectParticipantsSerializer.serialize(all_roles, user), safe=False)
        except Project.DoesNotExist:
            return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)


class ProjectInvitationAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        role = request.data['role']
        try:
            project = Project.objects.get(pk=pk, roles__user=user)
            code = ''.join(random.choices(string.ascii_letters, k=16))
            invitation = Invitation()
            invitation.code = code
            invitation.project = project
            invitation.role = role
            invitation.save()
            return JsonResponse({
                'code': code
            })
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)


class ProjectAccessTokenAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user

        try:
            tokens = ProjectAccessToken.objects.filter(
                project__pk=pk,
                project__roles__user=user,
            )
            result = []
            for token in tokens:
                if token.expiration and token.expiration < datetime.now():
                    try:
                        token.delete()
                    except Exception:
                        pass
                else:
                    result.append(token)

            serializer = ProjectAccessTokenSerializer(result, many=True)
            return JsonResponse(serializer.data, safe=False)
        except ProjectAccessToken.DoesNotExist:
            return JsonResponse([], safe=False)
        except Exception:
            return JsonResponse({
                'error': 'Invalid request'
            }, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, pk):
        user = request.user
        type = request.data.get('permission')
        if not type:
            return JsonResponse({
                'error': 'Permissions required'
            }, status=status.HTTP_400_BAD_REQUEST)
        expiration = request.data.get('expiration')

        try:
            project = Project.objects.get(
                pk=pk,
                roles__user=user
            )

            token = ProjectAccessToken()
            token.permission = type
            token.user = user
            token.token = ''.join(random.choices(string.ascii_letters, k=16))
            token.project = project
            if expiration:
                token.expiration = datetime.strptime(expiration, '%Y-%m-%d')
            token.save()
            serializer = ProjectAccessTokenSerializer(token)
            return JsonResponse(serializer.data)
        except Project.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid request'
            }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        user = request.user
        token = request.data.get('token')
        if not token:
            return JsonResponse({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            api_token = ProjectAccessToken.objects.get(
                token=token,
                project__roles__user=user
            )

            api_token.delete()

            tokens = ProjectAccessToken.objects.filter(
                project__pk=pk,
                project__roles__user=user,
            )
            serializer = ProjectAccessTokenSerializer(tokens, many=True)
            return JsonResponse(serializer.data, safe=False)

        except ProjectAccessToken.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)
