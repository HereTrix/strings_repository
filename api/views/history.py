from datetime import datetime
from django.http import HttpResponse, JsonResponse
from rest_framework import generics, permissions, status
from api.file_processors.history_file import HistoryFileWriter
from django.db.models import Prefetch

from api.models import Project, StringToken, Translation
from api.serializers import HistorySerializer


class ProjectHistoryAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        time_from = request.GET.get('from')
        time_to = request.GET.get('to')
        if not time_from and not time_to:
            return JsonResponse({
                'error': 'Missing time range'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            translations = Translation.objects.filter(
                token__project__pk=pk,
                token__project__roles__user=user
            )

            if time_from:
                date = datetime.strptime(time_from, '%Y-%m-%d')
                translations = translations.filter(
                    updated_at__gte=date
                )

            if time_to:
                date = datetime.strptime(time_to, '%Y-%m-%d')
                translations = translations.filter(
                    updated_at__lte=date
                )
            translations = translations.order_by('updated_at')

            serializer = HistorySerializer(translations, many=True)
            return JsonResponse(serializer.data, safe=False)
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)


class ProjectHistoryExportAPI(generics.GenericAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        time_from = request.GET.get('from')
        time_to = request.GET.get('to')
        if not time_from and not time_to:
            return JsonResponse({
                'error': 'Missing time range'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(
                pk=pk,
                roles__user=user
            )

            languages = [lang.code for lang in project.languages.all()]

            tokens = StringToken.objects.filter(
                project=project
            )

            if time_from:
                date = datetime.strptime(time_from, '%Y-%m-%d')
                tokens = tokens.filter(
                    translation__updated_at__gte=date
                )

            if time_to:
                date = datetime.strptime(time_to, '%Y-%m-%d')
                tokens = tokens.filter(
                    translation__updated_at__lte=date
                )

            tokens = tokens.prefetch_related(Prefetch(
                'translation',
                queryset=Translation.objects.select_related('language'))
            ).distinct()

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=report.xlsx'

            writer = HistoryFileWriter(data=tokens, languages=languages)
            writer.write(response=response)
            return response
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)
