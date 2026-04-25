from django.http import JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser
from api.models.project import Project, ProjectRole
from api.models.string_token import StringToken
from api.models.scope import Scope, ScopeImage
from api.serializers.scope import ScopeSerializer


def _get_project_member(user, pk):
    try:
        return Project.objects.get(pk=pk, roles__user=user), None
    except Project.DoesNotExist:
        return None, JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


def _get_project_admin(user, pk):
    try:
        return Project.objects.get(
            pk=pk, roles__user=user, roles__role__in=ProjectRole.change_language_roles
        ), None
    except Project.DoesNotExist:
        return None, JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


class ScopeListCreateAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        project, err = _get_project_member(request.user, pk)
        if err:
            return err
        scopes = Scope.objects.filter(project=project).prefetch_related('images')
        serializer = ScopeSerializer(scopes, many=True, context={'request': request})
        return JsonResponse(serializer.data, safe=False)

    def post(self, request, pk):
        project, err = _get_project_admin(request.user, pk)
        if err:
            return err
        name = request.data.get('name', '').strip()
        description = request.data.get('description', '')
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
        scope = Scope.objects.create(project=project, name=name, description=description)
        serializer = ScopeSerializer(scope, context={'request': request})
        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)


class ScopeDetailAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, scope_id):
        project, err = _get_project_admin(request.user, pk)
        if err:
            return err
        scope = Scope.objects.filter(pk=scope_id, project=project).prefetch_related('images').first()
        if not scope:
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        scope.description = request.data.get('description', scope.description)
        scope.save()
        serializer = ScopeSerializer(scope, context={'request': request})
        return JsonResponse(serializer.data)

    def delete(self, request, pk, scope_id):
        project, err = _get_project_admin(request.user, pk)
        if err:
            return err
        Scope.objects.filter(pk=scope_id, project=project).delete()
        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)


class ScopeTokensAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_scope(self, user, pk, scope_id):
        project, err = _get_project_admin(user, pk)
        if err:
            return None, err
        scope = Scope.objects.filter(pk=scope_id, project=project).first()
        if not scope:
            return None, JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return scope, None

    def post(self, request, pk, scope_id):
        scope, err = self._get_scope(request.user, pk, scope_id)
        if err:
            return err
        token_ids = request.data.get('token_ids', [])
        tokens = StringToken.objects.filter(pk__in=token_ids, project=scope.project)
        scope.tokens.add(*tokens)
        return JsonResponse({})

    def delete(self, request, pk, scope_id):
        scope, err = self._get_scope(request.user, pk, scope_id)
        if err:
            return err
        token_ids = request.data.get('token_ids', [])
        tokens = StringToken.objects.filter(pk__in=token_ids)
        scope.tokens.remove(*tokens)
        return JsonResponse({})


class ScopeImageAPI(generics.GenericAPIView):
    """POST: upload a new image to a scope. DELETE: remove a specific image by id."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def _get_scope(self, user, pk, scope_id):
        project, err = _get_project_admin(user, pk)
        if err:
            return None, err
        scope = Scope.objects.filter(pk=scope_id, project=project).prefetch_related('images').first()
        if not scope:
            return None, JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return scope, None

    def post(self, request, pk, scope_id):
        scope, err = self._get_scope(request.user, pk, scope_id)
        if err:
            return err
        image = request.FILES.get('image')
        if not image:
            return JsonResponse({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
        ScopeImage.objects.create(scope=scope, image=image)
        scope.refresh_from_db()
        serializer = ScopeSerializer(scope, context={'request': request})
        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk, scope_id):
        scope, err = self._get_scope(request.user, pk, scope_id)
        if err:
            return err
        image_id = request.data.get('image_id')
        if not image_id:
            return JsonResponse({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        img = ScopeImage.objects.filter(pk=image_id, scope=scope).first()
        if not img:
            return JsonResponse({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        img.image.delete(save=False)
        img.delete()
        scope.refresh_from_db()
        serializer = ScopeSerializer(scope, context={'request': request})
        return JsonResponse(serializer.data)
