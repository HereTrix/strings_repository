from datetime import datetime
from django.http import HttpResponse, JsonResponse
from rest_framework import generics, permissions, status
from api.file_processors.history_file import HistoryFileWriter
from django.db.models import Prefetch

from api.models import HistoryRecord, Project, StringToken, Translation
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
            records = HistoryRecord.objects.filter(
                project__pk=pk,
                project__roles__user=user
            )

            if time_from:
                date = datetime.strptime(time_from, '%Y-%m-%d')
                records = records.filter(
                    updated_at__gte=date
                )

            if time_to:
                date = datetime.strptime(time_to, '%Y-%m-%d')
                records = records.filter(
                    updated_at__lte=date
                )
            records = records.order_by('updated_at')

            serializer = HistorySerializer(records, many=True)
            return JsonResponse(serializer.data, safe=False)
        except Exception as e:
            print(e)
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
            records = HistoryRecord.objects.filter(
                project__pk=pk,
                project__roles__user=user
            )

            if time_from:
                date = datetime.strptime(time_from, '%Y-%m-%d')
                records = records.filter(
                    updated_at__gte=date
                )

            if time_to:
                date = datetime.strptime(time_to, '%Y-%m-%d')
                records = records.filter(
                    updated_at__lte=date
                )
            records = records.order_by('updated_at')

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=report.xlsx'

            writer = HistoryFileWriter(data=records)
            writer.write(response=response)
            return response
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)
