import random
import string
from datetime import datetime

from django.http import JsonResponse
from rest_framework import generics, permissions, status

from api import dispatcher
from api.models.project import Project, Invitation, ProjectAccessToken, ProjectRole
from api.serializers.project import ProjectAccessTokenSerializer, ProjectParticipantsSerializer


def generate_token(length=16):
    return ''.join(random.choices(string.ascii_letters, k=length))


def delete_expired_tokens(tokens):
    now = datetime.now()
    return [token for token in tokens if not (token.expiration and token.expiration < now)]


class RolesAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user

        role = ProjectRole.objects.filter(
            project__pk=pk,
            user=user,
        ).first()

        if role is None:
            return JsonResponse({
                'error': 'User is not a member of this project'
            }, status=status.HTTP_403_FORBIDDEN)

        if role.role == ProjectRole.Role.owner:
            data = [r.value for r in ProjectRole.Role]
        elif role.role == ProjectRole.Role.admin:
            data = ProjectRole.common_roles
        elif role.role == ProjectRole.Role.editor:
            data = ProjectRole.translator_roles
        else:
            return JsonResponse({
                'error': 'User is not allowed to set roles'
            }, status=status.HTTP_403_FORBIDDEN)

        return JsonResponse(data, safe=False)


class ProjectParticipantsAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user

        try:
            project = Project.objects.get(
                pk=pk,
                roles__user=user,
                roles__role__in=ProjectRole.change_participants_roles
            )
        except Project.DoesNotExist:
            return JsonResponse({
                'error': 'Participants can not be viewed'
            }, status=status.HTTP_403_FORBIDDEN)

        return JsonResponse(ProjectParticipantsSerializer.serialize(project.roles.all(), user), safe=False)

    def post(self, request, pk):
        user = request.user
        user_id = request.data['user_id']
        new_role = request.data['role']

        try:
            project = Project.objects.get(
                pk=pk,
                roles__user=user,
                roles__role__in=ProjectRole.change_participants_roles
            )
        except Project.DoesNotExist:
            return JsonResponse({
                'error': 'Not allowed'
            }, status=status.HTTP_403_FORBIDDEN)

        all_roles = project.roles.all()

        user_role = next((r for r in all_roles if r.user.id == user_id), None)
        if user_role is None:
            return JsonResponse({
                'error': 'User not found in project'
            }, status=status.HTTP_404_NOT_FOUND)

        if user_role.role == ProjectRole.Role.owner:
            current_role = next(
                (r for r in all_roles if r.user.id == user.id), None)
            if current_role is None or current_role.role != ProjectRole.Role.owner:
                return JsonResponse({
                    'error': 'Not allowed'
                }, status=status.HTTP_403_FORBIDDEN)

        user_role.role = new_role
        user_role.save()

        dispatcher.dispatch_event(
            project_id=pk,
            event_type='member.role_changed',
            payload={'user_id': user_id, 'role': new_role},
            actor=user.email,
        )

        return JsonResponse(ProjectParticipantsSerializer.serialize(all_roles, user), safe=False)

    def delete(self, request, pk):
        user = request.user
        user_id = request.data['user_id']

        try:
            project = Project.objects.get(
                pk=pk,
                roles__user=user,
                roles__role__in=ProjectRole.change_participants_roles
            )
        except Project.DoesNotExist:
            return JsonResponse({
                'error': 'Not allowed'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            role = ProjectRole.objects.get(project=project, user__pk=user_id)
        except ProjectRole.DoesNotExist:
            return JsonResponse({
                'error': 'User not found in project'
            }, status=status.HTTP_404_NOT_FOUND)

        role.delete()

        ProjectAccessToken.objects.filter(
            project=project, user__pk=user_id).delete()

        return JsonResponse(ProjectParticipantsSerializer.serialize(project.roles.all(), user), safe=False)


class ProjectInvitationAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        role = request.data['role']

        try:
            project = Project.objects.get(pk=pk, roles__user=user)
        except Project.DoesNotExist:
            return JsonResponse({
                'error': 'Unable to generate code'
            }, status=status.HTTP_403_FORBIDDEN)

        user_role = project.roles.get(user=user)

        if user_role.role == ProjectRole.Role.owner:
            pass  # may invite any role
        elif user_role.role == ProjectRole.Role.admin:
            if role not in ProjectRole.common_roles:
                return JsonResponse({
                    'error': 'Unable to generate code'
                }, status=status.HTTP_400_BAD_REQUEST)
        elif user_role.role == ProjectRole.Role.editor:
            if role not in ProjectRole.translator_roles:
                return JsonResponse({
                    'error': 'Unable to generate code'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return JsonResponse({
                'error': 'Unable to generate code'
            }, status=status.HTTP_403_FORBIDDEN)

        code = generate_token()
        invitation = Invitation()
        invitation.code = code
        invitation.project = project
        invitation.role = role
        invitation.save()

        dispatcher.dispatch_event(
            project_id=pk,
            event_type='member.invited',
            payload={'role': role},
            actor=user.email,
        )

        return JsonResponse({'code': code})


class ProjectAccessTokenAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user

        tokens = ProjectAccessToken.objects.filter(
            project__pk=pk,
            project__roles__user=user,
        )

        valid_tokens = delete_expired_tokens(tokens)

        # Bulk-delete expired tokens
        valid_ids = {t.pk for t in valid_tokens}
        tokens.exclude(pk__in=valid_ids).delete()

        serializer = ProjectAccessTokenSerializer(valid_tokens, many=True)
        return JsonResponse(serializer.data, safe=False)

    def post(self, request, pk):
        user = request.user
        permission = request.data.get('permission')
        if not permission:
            return JsonResponse({
                'error': 'Permissions required'
            }, status=status.HTTP_400_BAD_REQUEST)
        expiration = request.data.get('expiration')

        try:
            project = Project.objects.get(pk=pk, roles__user=user)
        except Project.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid request'
            }, status=status.HTTP_400_BAD_REQUEST)

        token = ProjectAccessToken()
        token.permission = permission
        token.user = user
        token.token = generate_token()
        token.project = project
        if expiration:
            token.expiration = datetime.strptime(expiration, '%Y-%m-%d')
        token.save()

        serializer = ProjectAccessTokenSerializer(token)
        return JsonResponse(serializer.data)

    def delete(self, request, pk):
        user = request.user
        token_value = request.data.get('token')
        if not token_value:
            return JsonResponse({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            api_token = ProjectAccessToken.objects.get(
                token=token_value,
                project__roles__user=user
            )
        except ProjectAccessToken.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)

        api_token.delete()

        tokens = ProjectAccessToken.objects.filter(
            project__pk=pk,
            project__roles__user=user,
        )
        serializer = ProjectAccessTokenSerializer(tokens, many=True)
        return JsonResponse(serializer.data, safe=False)
