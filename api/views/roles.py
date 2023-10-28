import random
import string
from django.http import JsonResponse
from rest_framework import generics, permissions, status

from api.models import Invitation, Project, ProjectRole
from api.serializers import ProjectParticipantsSerializer


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
