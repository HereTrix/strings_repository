from django.http import JsonResponse


def error_response(message, status_code):
    return JsonResponse({'error': str(message)}, status=status_code)


from api.models.project import Project, ProjectRole


def get_project_any_role(pk: int, user) -> Project | None:
    return Project.objects.filter(pk=pk, roles__user=user).first()


def get_project_admin(pk: int, user) -> Project | None:
    return Project.objects.filter(
        pk=pk,
        roles__user=user,
        roles__role__in=ProjectRole.change_participants_roles,
    ).first()


def get_project_editor_plus(pk: int, user) -> Project | None:
    return Project.objects.filter(
        pk=pk,
        roles__user=user,
        roles__role__in=ProjectRole.change_token_roles,
    ).first()
