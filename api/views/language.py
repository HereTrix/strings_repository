from django.http import JsonResponse
from rest_framework import generics, permissions, status
import django.core.exceptions as exception

from api.models import Language, Project, ProjectRole
from api.serializers import LanguageSerializer


class LanguageAPI(generics.GenericAPIView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        code = request.data['code']
        project_id = request.data['project']

        if code is None:
            return JsonResponse({
                'error': 'Code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        if project_id is None:
            return JsonResponse({
                'error': 'Project is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(
                pk=project_id, roles__user=user, roles__role__in=ProjectRole.change_language_roles)
        except Project.DoesNotExist:
            return JsonResponse(status=status.HTTP_404_NOT_FOUND)
        except exception.ValidationError as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            language = Language.objects.get(code=code, project=project_id)
            return JsonResponse({
                'error': 'Project already has this language'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Language.DoesNotExist:
            language = Language()
            language.project = project
            language.code = code.upper()
            language.save()
        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)

    def delete(self, request):
        user = request.user
        code = request.data['code']
        project_id = request.data['project']

        if code is None:
            return JsonResponse({
                'error': 'Code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        if project_id is None:
            return JsonResponse({
                'error': 'Project is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(
                pk=project_id, roles__user=user, roles__role__in=ProjectRole.change_language_roles)
        except Project.DoesNotExist as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except exception.ValidationError as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            language = Language.objects.get(code=code, project=project_id)
            language.delete()
            return JsonResponse({}, status=status.HTTP_200_OK)
        except Language.DoesNotExist:
            return JsonResponse({
                'error': "Language doesn't exist"
            }, status=status.HTTP_404_NOT_FOUND)
