from django.db.models import Q

from api.models.history import HistoryRecord
from api.models.string_token import StringToken
from api.models.tag import Tag
from api.models.translations import Translation


def list_tokens(args, access):
    qs = StringToken.objects.filter(project=access.project)
    q = args.get('search')
    tags = args.get('tags')
    limit = max(1, min(int(args.get('limit', 50)), 200))
    offset = max(0, int(args.get('offset', 0)))

    if q:
        qs = qs.filter(Q(token__icontains=q) | Q(
            translation__translation__icontains=q))
    if tags:
        for tag in tags.split(','):
            qs = qs.filter(tags__tag=tag.strip())

    qs = qs.distinct().prefetch_related('tags')
    total = qs.count()
    page = list(qs[offset:offset + limit])

    return {
        "count": total,
        "results": [
            {
                "id": t.id,
                "token": t.token,
                "comment": t.comment,
                "status": t.status,
                "tags": [tag.tag for tag in t.tags.all()],
            }
            for t in page
        ],
    }


def get_token(args, access):
    token_key = args.get('token_key')
    try:
        token = StringToken.objects.prefetch_related('tags', 'translation__language').get(
            token=token_key, project=access.project
        )
    except StringToken.DoesNotExist:
        raise ValueError(f"Token '{token_key}' not found")

    return {
        "id": token.id,
        "token": token.token,
        "comment": token.comment,
        "status": token.status,
        "tags": [tag.tag for tag in token.tags.all()],
        "translations": [
            {"language": t.language.code, "text": t.translation, "status": t.status}
            for t in token.translation.select_related('language').all()
        ],
    }


def create_token(args, access):
    if access.permission == access.__class__.AccessTokenPermissions.read:
        raise PermissionError("Write permission required")

    token_key = args.get('token_key', '').strip()
    if not token_key:
        raise ValueError("token_key is required")

    if StringToken.objects.filter(token=token_key, project=access.project).exists():
        raise ValueError(
            f"Token '{token_key}' already exists. Use set_translation to add translations.")

    token = StringToken.objects.create(
        token=token_key,
        comment=args.get('comment', ''),
        project=access.project,
    )

    tag_names = args.get('tags') or []
    for tag_name in tag_names:
        tag, _ = Tag.objects.get_or_create(tag=tag_name)
        token.tags.add(tag)

    HistoryRecord.objects.create(
        project=access.project,
        token=token.token,
        status=HistoryRecord.Status.created,
        editor=access.user,
    )

    return {"id": token.id, "token": token.token, "comment": token.comment, "status": token.status, "tags": tag_names}


def set_translation(args, access):
    if access.permission == access.__class__.AccessTokenPermissions.read:
        raise PermissionError("Write permission required")

    token_key = args.get('token_key')
    language_code = args.get('language_code', '').upper()
    text = args.get('text', '')

    try:
        token = StringToken.objects.get(token=token_key, project=access.project)
    except StringToken.DoesNotExist:
        raise ValueError(
            f"Token '{token_key}' not found. Create it first with create_token.")

    Translation.create_or_update_translation(
        user=access.user,
        token=token,
        code=language_code,
        project_id=access.project.id,
        text=text,
    )
    return {"token": token_key, "language": language_code, "text": text}


def batch_create_tokens(args, access):
    if access.permission == access.__class__.AccessTokenPermissions.read:
        raise PermissionError("Write permission required")

    entries = args.get('entries') or []
    created, skipped, failed = [], [], []

    for entry in entries:
        token_key = entry.get('token_key', '').strip()
        if not token_key:
            failed.append({"token_key": token_key, "error": "token_key is required"})
            continue

        try:
            if StringToken.objects.filter(token=token_key, project=access.project).exists():
                skipped.append(token_key)
                continue

            token = StringToken.objects.create(
                token=token_key,
                comment=entry.get('comment', ''),
                project=access.project,
            )

            language_code = entry.get('language_code', '').upper()
            text = entry.get('text', '')
            if language_code and text:
                Translation.create_or_update_translation(
                    user=access.user,
                    token=token,
                    code=language_code,
                    project_id=access.project.id,
                    text=text,
                )

            HistoryRecord.objects.create(
                project=access.project,
                token=token.token,
                status=HistoryRecord.Status.created,
                editor=access.user,
            )
            created.append(token_key)

        except Exception as exc:
            failed.append({"token_key": token_key, "error": str(exc)})

    return {"created": created, "skipped": skipped, "failed": failed}
