from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import status, views

from api import dispatcher
from api.file_processors.file_processor import FileImporter
from api.models.project import Project, ProjectRole
from api.models.language import Language
from api.models.string_token import StringToken
from api.models.translations import Translation
from api.models.tag import Tag


class ImportAPI(views.APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        user = request.user
        code = request.POST.get('code')
        tags = request.POST.get('tags')
        project_id = request.POST.get('project_id')
        file = request.FILES.get('file')
        deprecate_missing = request.POST.get(
            'deprecate_missing', 'false').lower() == 'true'

        if not file:
            return Response({
                'error': 'No localization file'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not project_id:
            return Response({
                'error': 'No project_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Regular import requires editor or above
        try:
            project = Project.objects.get(
                pk=project_id,
                roles__user=user,
                roles__role__in=ProjectRole.change_token_roles,
            )
        except Project.DoesNotExist:
            return Response({
                'error': 'Not allowed'
            }, status=status.HTTP_403_FORBIDDEN)

        # Deprecating missing tokens is a bulk destructive action — owner/admin only
        if deprecate_missing:
            if tags:
                return Response({
                    'error': 'deprecate_missing cannot be used with a tag filter — '
                             'a partial import does not represent the full token set.'
                }, status=status.HTTP_400_BAD_REQUEST)

            user_role = project.roles.get(user=user).role
            if user_role not in ProjectRole.change_participants_roles:
                return Response({
                    'error': 'Deprecating missing tokens requires owner or admin role.'
                }, status=status.HTTP_403_FORBIDDEN)

        try:
            importer = FileImporter(file=file)

            if importer.needs_language_code() and not code:
                return Response({
                    'error': 'No language code'
                }, status=status.HTTP_400_BAD_REQUEST)

            records = importer.parse()
        except FileImporter.UnsupportedFile:
            return Response({
                'error': 'Unsupported file format'
            }, status=status.HTTP_404_NOT_FOUND)

        tag_models = []
        if tags:
            for tag in tags.split(','):
                try:
                    tag_model = Tag.objects.get(tag=tag)
                except Tag.DoesNotExist:
                    tag_model = Tag()
                    tag_model.tag = tag
                    tag_model.save()
                tag_models.append(tag_model)

        imported_count = 0
        imported_keys = set()

        for record in records:
            try:
                if importer.needs_language_code():
                    Translation.import_record(
                        user=user,
                        project_id=project_id,
                        code=code,
                        record=record,
                        tags=tag_models
                    )
                else:
                    Translation.import_record(
                        user=user,
                        project_id=project_id,
                        code=record.code,
                        record=record,
                        tags=tag_models
                    )
                imported_keys.add(record.token)
                imported_count += 1
            except Project.DoesNotExist:
                return Response({
                    'error': 'Unable to import into project'
                }, status=status.HTTP_404_NOT_FOUND)
            except Language.DoesNotExist:
                return Response({
                    'error': 'Unable to import with language code'
                }, status=status.HTTP_404_NOT_FOUND)

        deprecated_count = 0
        if deprecate_missing and imported_keys:
            deprecated_qs = StringToken.objects.filter(
                project=project,
                status=StringToken.Status.active,
            ).exclude(token__in=imported_keys)
            deprecated_count = deprecated_qs.count()
            deprecated_qs.update(status=StringToken.Status.deprecated)

        dispatcher.dispatch_event(
            project_id=project_id,
            event_type='import.completed',
            payload={
                'count': imported_count,
                'deprecated_count': deprecated_count,
                'language': code,
                'filename': file.name,
            },
            actor=user.email,
        )

        return Response({
            'imported': imported_count,
            'deprecated': deprecated_count,
        })
