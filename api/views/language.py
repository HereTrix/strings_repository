from rest_framework.response import Response
from rest_framework import generics, status
import django.core.exceptions as exception

from api import dispatcher
from api.models.project import Project, ProjectRole
from api.models.language import Language
from api.serializers.language import LanguageSerializer


class LanguageAPI(generics.GenericAPIView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer

    def post(self, request):
        user = request.user
        code = request.data['code']
        project_id = request.data['project']

        if code is None:
            return Response({
                'error': 'Code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        if project_id is None:
            return Response({
                'error': 'Project is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(
                pk=project_id, roles__user=user,
                roles__role__in=ProjectRole.change_language_roles
            )
        except Project.DoesNotExist:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        try:
            Language.objects.get(code=code, project=project)
            return Response({
                'error': 'Project already has this language'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Language.DoesNotExist:
            language = Language()
            language.project = project
            language.code = code.upper()
            language.save()

        dispatcher.dispatch_event(
            project_id=project.pk,
            event_type='language.added',
            payload={'language': code.upper()},
            actor=user.email,
        )

        return Response({}, status=status.HTTP_204_NO_CONTENT)

    def delete(self, request):
        user = request.user
        code = request.data['code']
        project_id = request.data['project']

        if code is None:
            return Response({
                'error': 'Code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        if project_id is None:
            return Response({
                'error': 'Project is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(
                pk=project_id, roles__user=user, roles__role__in=ProjectRole.change_language_roles)
        except Project.DoesNotExist as e:
            return Response({
                'error': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            language = Language.objects.get(code=code, project=project)
            language.delete()
            dispatcher.dispatch_event(
                project_id=project.pk,
                event_type='language.removed',
                payload={'language': code.upper()},
                actor=user.email,
            )
            return Response({}, status=status.HTTP_200_OK)
        except Language.DoesNotExist:
            return Response({
                'error': "Language doesn't exist"
            }, status=status.HTTP_404_NOT_FOUND)


class SetDefaultLanguageAPI(generics.GenericAPIView):

    def put(self, request, pk, code):
        try:
            project = Project.objects.get(
                pk=pk,
                roles__user=request.user,
                roles__role__in=ProjectRole.change_language_roles,
            )
        except Project.DoesNotExist:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        try:
            language = Language.objects.get(code=code.upper(), project=project)
        except Language.DoesNotExist:
            return Response({'error': 'Language not found'}, status=status.HTTP_404_NOT_FOUND)

        Language.objects.filter(
            project=project, is_default=True).update(is_default=False)
        language.is_default = True
        language.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
