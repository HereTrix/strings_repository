from django.db import transaction
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from api.filters.string_token_filter import StringTokenFilter
from api.filters.translation_filter import TranslationTokenFilter
from api.languages.langcoder import LANGUAGE_CODE_KEY, Langcoder
from api.models import Language, Project, ProjectRole, StringToken, Tag
from api.paginators.string_token_paginator import TranslationsPagination
from api.serializers import AvailableLanguageSerializer, ProjectSerializer, StringTokenModelSerializer, StringTokenSerializer, TagSerializer, LanguageSerializer, CreateProjectSerializer, ProjectDetailSerializer


class ProjectAPI(generics.RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectDetailSerializer

    def get_queryset(self):
        return Project.objects.filter(
            roles__user=self.request.user
        ).prefetch_related('languages', 'roles')

    def destroy(self, request, *args, **kwargs):
        project = Project.objects.filter(
            pk=self.kwargs['pk'],
            roles__user=request.user,
            roles__role__in=ProjectRole.change_participants_roles
        )
        project.delete()
        return JsonResponse(status=status.HTTP_204_NO_CONTENT)


class CreateProjectAPI(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CreateProjectSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            project = serializer.save()
            ProjectRole.objects.create(
                user=self.request.user,
                role=ProjectRole.Role.owner,
                project=project
            )


class ProjectListAPI(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(
            roles__user=self.request.user
        ).prefetch_related('roles')


class ProjectAvailableLanguagesAPI(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AvailableLanguageSerializer

    def get_queryset(self):
        return Language.objects.filter(
            project__id=self.kwargs['pk'],
            project__roles__user=self.request.user,
            project__roles__role__in=ProjectRole.change_language_roles
        )

    def get_used_codes(self):
        return set(self.get_queryset().values_list('code', flat=True))

    def list(self, request, *args, **kwargs):
        used_codes = self.get_used_codes()
        unused = [
            lang for lang in Langcoder.all_languages()
            if lang[LANGUAGE_CODE_KEY] not in used_codes
        ]
        serializer = self.get_serializer(unused, many=True)
        return JsonResponse(serializer.data)


class LanguageListAPI(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LanguageSerializer

    def get_queryset(self):
        return Language.objects.filter(
            project__id=self.kwargs['pk'],
            project__roles__user=self.request.user
        ).distinct()


class StringTokenListAPI(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StringTokenSerializer
    pagination_class = TranslationsPagination
    filterset_class = StringTokenFilter

    def get_queryset(self):
        return StringToken.objects.filter(
            project__id=self.kwargs['pk'],
            project__roles__user=self.request.user
        ).prefetch_related('tags', 'translation').distinct()


class TranslationsListAPI(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StringTokenModelSerializer
    pagination_class = TranslationsPagination
    filterset_class = TranslationTokenFilter

    def get_queryset(self):
        return StringToken.objects.filter(
            project__pk=self.kwargs['pk'],
            project__roles__user=self.request.user
        ).prefetch_related('translation', 'tags').distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['code'] = self.kwargs.get('code')
        return context


class ProjectTagsAPI(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(
            tokens__project__pk=self.kwargs['pk'],
            tokens__project__roles__user=self.request.user
        ).distinct()
