from django.db import transaction
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from api.filters.string_token_filter import StringTokenFilter
from api.filters.translation_filter import TranslationTokenFilter
from api.languages.langcoder import LANGUAGE_CODE_KEY, Langcoder
from api.models.language import Language
from api.models.project import Project, ProjectRole
from api.models.tag import Tag
from api.models.translations import StringToken, Translation
from api.paginators.string_token_paginator import TranslationsPagination
from api.serializers.project import ProjectSerializer, CreateProjectSerializer, ProjectDetailSerializer
from api.serializers.language import AvailableLanguageSerializer, LanguageSerializer
from api.serializers.translation import StringTokenModelSerializer, StringTokenSerializer


class ProjectAPI(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectDetailSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

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
        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)


class CreateProjectAPI(generics.CreateAPIView):
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
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(
            roles__user=self.request.user
        ).prefetch_related('roles')


class ProjectAvailableLanguagesAPI(generics.ListAPIView):
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
        return JsonResponse(serializer.data, safe=False)


class LanguageListAPI(generics.ListAPIView):
    serializer_class = LanguageSerializer

    def get_queryset(self):
        return Language.objects.filter(
            project__id=self.kwargs['pk'],
            project__roles__user=self.request.user
        ).distinct()


class StringTokenListAPI(generics.ListAPIView):
    serializer_class = StringTokenSerializer
    pagination_class = TranslationsPagination
    filterset_class = StringTokenFilter

    def get_queryset(self):
        return StringToken.objects.filter(
            project__id=self.kwargs['pk'],
            project__roles__user=self.request.user
        ).prefetch_related('tags', 'translation').distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        default_lang = Language.objects.filter(
            project__pk=self.kwargs['pk'],
            is_default=True
        ).first()
        context['default_code'] = default_lang.code if default_lang else None
        return context


class TranslationsListAPI(generics.ListAPIView):
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
        code = self.kwargs.get('code', '').upper()
        context['code'] = code
        default_lang = Language.objects.filter(
            project__pk=self.kwargs['pk'],
            is_default=True
        ).first()
        context['default_code'] = default_lang.code if default_lang else None
        from api.models.glossary import GlossaryTerm
        terms = GlossaryTerm.objects.filter(
            project__pk=self.kwargs['pk']
        ).prefetch_related('translations')
        glossary = []
        for term in terms:
            pt = next(
                (t.preferred_translation for t in term.translations.all()
                 if t.language_code.upper() == code),
                ''
            )
            glossary.append({
                'term': term.term,
                'definition': term.definition,
                'case_sensitive': term.case_sensitive,
                'preferred_translation': pt,
            })
        context['glossary_terms'] = glossary
        return context


class LanguageProgressAPI(generics.GenericAPIView):

    def get(self, request, pk):
        try:
            project = Project.objects.get(pk=pk, roles__user=request.user)
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        total = StringToken.objects.filter(
            project=project, status='active').count()
        result = {}
        for language in project.languages.all():
            translated = Translation.objects.filter(
                token__project=project,
                token__status='active',
                language=language,
            ).exclude(translation='').count()
            percent = round(translated / total * 100, 1) if total > 0 else 0.0
            result[language.code] = {
                'translated': translated,
                'total': total,
                'percent': percent,
            }
        return JsonResponse(result)


class ProjectTagsAPI(generics.GenericAPIView):

    def get(self, request, pk):
        tags = list(
            Tag.objects.filter(
                tokens__project__pk=pk,
                tokens__project__roles__user=request.user
            ).distinct().values_list('tag', flat=True)
        )
        return JsonResponse(tags, safe=False)
