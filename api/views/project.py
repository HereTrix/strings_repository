from django.http import JsonResponse
from django.db.models import Q
from rest_framework import generics, permissions, status
from api.languages.langcoder import LANGUAGE_CODE_KEY, Langcoder
from api.models import Language, Project, ProjectRole, StringToken, Tag
from api.serializers import ProjectSerializer, StringTokenModelSerializer, StringTokenSerializer
from api.transport_models import APIProject
from repository.settings import LANGUAGE_CODE


class ProjectAPI(generics.GenericAPIView):

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            user = request.user
            project = Project.objects.get(
                pk=pk, roles__user=user)

            api_languages = [{'code': lang.code, 'name': Langcoder.language(
                lang.code)} for lang in project.languages.all()]

            role = project.roles.get(user=user)

            api_project = APIProject(
                project=project, languages=api_languages, role=role.role)

            return JsonResponse(api_project.__dict__, safe=False)
        except Project.DoesNotExist as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        user = request.user
        try:
            project = Project.objects.filter(
                pk=pk, roles__user=user, roles__role__in=ProjectRole.change_participants_roles)
            project.delete()
            return JsonResponse({})
        except Project.DoesNotExist as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)


class CreateProjectAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            project = Project()
            name = request.data['name']
            if name is None:
                return JsonResponse({
                    "error": "Name is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            project.name = name
            project.description = request.data['description']
            project.save()
            role = ProjectRole()
            role.user = user
            role.role = ProjectRole.Role.owner
            role.project = project
            role.save()
            serializer = ProjectSerializer(project)
            return JsonResponse(serializer.data)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)


class ProjectListAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            projects = Project.objects.filter(
                roles__user=user
            ).prefetch_related('roles')

            result = []
            for project in projects:
                role = project.roles.get(user=user)
                result.append({
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'role': role.role
                })
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)


class ProjectAvailableLanguagesAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            user = request.user
            languages = Language.objects.filter(project__id=pk,
                                                project__roles__user=user,
                                                project__roles__role__in=ProjectRole.change_language_roles)

            unused = list(filter(lambda val: not any(
                used.code == val[LANGUAGE_CODE_KEY] for used in languages), Langcoder.all_languages()))

            return JsonResponse(unused, safe=False)
        except Language.DoesNotExist:
            unused = Langcoder.all_languages()
            return JsonResponse(unused, safe=False)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)


class LanguageListAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        try:
            languages = Language.objects.filter(
                project__id=pk,
                project__roles__user=user
            )

            result = [{"code": lang.code, "name": Langcoder.language(lang.code)}
                      for lang in languages]
            return JsonResponse(result, safe=False, status=status.HTTP_200_OK)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class StringTokenListAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        query = request.GET.get('q')
        tags = request.GET.get('tags')
        offset = request.GET.get('offset')
        limit = request.GET.get('limit')
        isNew = request.GET.get('new')

        if not offset:
            offset = 0
        else:
            offset = int(offset)

        try:
            tokens = StringToken.objects.filter(
                project__id=pk,
                project__roles__user=user
            )

            if query:
                tokens = tokens.filter(token__icontains=query)

            if tags:
                items = tags.split(',')
                tokens = tokens.filter(
                    tags__tag__in=items
                ).distinct()

            if isNew:
                tokens = tokens.filter(
                    Q(translation__translation__exact='') | Q(
                        translation__translation__isnull=True
                    )
                )

            if limit:
                limit = int(limit)
                tokens = tokens.prefetch_related('tags')[offset:offset+limit]
            else:
                tokens = tokens.prefetch_related('tags')

            serializer = StringTokenSerializer(tokens, many=True)
            return JsonResponse(serializer.data, safe=False)
        except Exception as e:
            # except StringToken.DoesNotExist as e:
            return JsonResponse({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TranslationsListAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, code):
        user = request.user
        tags = request.GET.get('tags')
        query = request.GET.get('q')
        offset = request.GET.get('offset')
        limit = request.GET.get('limit')
        untranslated = request.GET.get('untranslated')

        if not offset:
            offset = 0
        else:
            offset = int(offset)

        try:
            tokens = StringToken.objects.filter(
                project__pk=pk,
                project__roles__user=user
            ).prefetch_related('translation', 'tags').distinct()

            if query:
                tokens = tokens.filter(
                    translation__translation__icontains=query
                ) | tokens.filter(
                    token__icontains=query
                )

            if tags:
                tokens = tokens.filter(
                    tags__tag__in=tags.split(',')
                )

            if untranslated and untranslated == 'true':
                tokens = tokens.filter(
                    Q(translation__translation__exact='') | Q(
                        translation__translation__isnull=True)
                )

            if limit:
                limit = int(limit)
                tokens = tokens.prefetch_related('tags')[offset:offset+limit]
            else:
                tokens = tokens.prefetch_related('tags')

            result = [StringTokenModelSerializer(token=token, code=code).toJson()
                      for token in tokens]

            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status.HTTP_404_NOT_FOUND)


class ProjectTagsAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        try:
            tags = Tag.objects.filter(
                tokens__project__pk=pk,
                tokens__project__roles__user=user
            ).distinct()
            data = [tag.tag for tag in tags]
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({
                'error': e
            }, status=status.HTTP_400_BAD_REQUEST)
