from rest_framework.response import Response
from rest_framework import generics, status

from api.crypto import decrypt, encrypt
from api.models.project import Project, ProjectRole
from api.models.webhook import WebhookEndpoint


_HTTP_STATUS_HINTS = {
    400: 'The endpoint rejected the request as invalid.',
    401: 'The endpoint requires authentication. Check your auth token.',
    403: 'The endpoint denied access. Check your auth token.',
    404: 'The endpoint URL was not found. Check the URL.',
    405: 'The endpoint does not accept POST requests.',
    410: 'The endpoint URL no longer exists.',
    429: 'The endpoint is rate-limiting requests. Try again later.',
    500: 'The endpoint returned an internal server error.',
    502: 'The endpoint\'s upstream server is unavailable.',
    503: 'The endpoint is temporarily unavailable.',
    504: 'The endpoint timed out while processing the request.',
}


def _http_error_message(status_code: int, raw: str | None) -> str:
    hint = _HTTP_STATUS_HINTS.get(status_code)
    if hint:
        return f'HTTP {status_code}: {hint}'
    if status_code >= 500:
        return f'HTTP {status_code}: The endpoint returned a server error.'
    if status_code >= 400:
        return f'HTTP {status_code}: The endpoint rejected the request.'
    return f'HTTP {status_code}: Unexpected response.'


def _network_error_message(raw: str) -> str:
    r = raw.lower()
    if 'connection refused' in r:
        return 'Connection refused — the endpoint host is not accepting connections.'
    if 'name or service not known' in r or 'nodename nor servname' in r or 'getaddrinfo failed' in r:
        return 'DNS lookup failed — the endpoint hostname could not be resolved. Check the URL.'
    if 'timed out' in r or 'timeout' in r:
        return 'Connection timed out — the endpoint did not respond within 10 seconds.'
    if 'unknown url type' in r:
        return 'Invalid URL — the webhook URL must start with http:// or https://.'
    if 'ssl' in r or 'certificate' in r:
        return 'SSL/TLS error — the endpoint\'s certificate could not be verified.'
    return f'Delivery failed: {raw}'


def _serialize_endpoint(endpoint: WebhookEndpoint, reveal_secret: bool = False) -> dict:
    return {
        'id': endpoint.pk,
        'title': endpoint.title,
        'url': decrypt(endpoint.url),
        'has_auth_token': bool(endpoint.auth_token),
        'signing_secret': endpoint.signing_secret if reveal_secret else '••••••••',
        'template': endpoint.template,
        'events': endpoint.events,
        'is_active': endpoint.is_active,
        'created_at': endpoint.created_at.isoformat(),
        'updated_at': endpoint.updated_at.isoformat(),
    }


def _get_project_for_admin(pk: int, user) -> Project | None:
    """Return project if user is owner or admin, else None."""
    return Project.objects.filter(
        pk=pk,
        roles__user=user,
        roles__role__in=ProjectRole.change_participants_roles,
    ).first()


class WebhookListAPI(generics.GenericAPIView):

    def get(self, request, pk):
        project = _get_project_for_admin(pk, request.user)
        if not project:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        endpoints = project.webhooks.all()
        return Response([_serialize_endpoint(e) for e in endpoints])

    def post(self, request, pk):
        project = _get_project_for_admin(pk, request.user)
        if not project:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        url = request.data.get('url', '').strip()
        title = request.data.get('title', '').strip()
        if not url:
            return Response({'error': 'url is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not title:
            return Response({'error': 'title is required'}, status=status.HTTP_400_BAD_REQUEST)

        events = request.data.get('events', [])
        unknown = [e for e in events if e not in WebhookEndpoint.EVENTS]
        if unknown:
            return Response(
                {'error': f'Unknown event types: {unknown}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        endpoint = WebhookEndpoint()
        endpoint.project = project
        endpoint.title = title
        endpoint.url = encrypt(url)
        endpoint.template = request.data.get('template', '')
        endpoint.events = events
        endpoint.is_active = request.data.get('is_active', True)

        auth_token = request.data.get('auth_token', '').strip()
        if auth_token:
            endpoint.auth_token = encrypt(auth_token)

        endpoint.save()

        # Reveal signing_secret only on creation so the user can copy it.
        return Response(_serialize_endpoint(endpoint, reveal_secret=True), status=status.HTTP_201_CREATED)


class WebhookDetailAPI(generics.GenericAPIView):

    def _get_endpoint(self, pk: int, webhook_id: int, user):
        project = _get_project_for_admin(pk, user)
        if not project:
            return None, Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            return project.webhooks.get(pk=webhook_id), None
        except WebhookEndpoint.DoesNotExist:
            return None, Response({'error': 'Webhook not found'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk, webhook_id):
        endpoint, err = self._get_endpoint(pk, webhook_id, request.user)
        if err:
            return err
        return Response(_serialize_endpoint(endpoint))

    def put(self, request, pk, webhook_id):
        endpoint, err = self._get_endpoint(pk, webhook_id, request.user)
        if err:
            return err

        if 'title' in request.data:
            title = request.data['title'].strip()
            if not title:
                return Response({'error': 'title cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
            endpoint.title = title

        if 'url' in request.data:
            url = request.data['url'].strip()
            if not url:
                return Response({'error': 'url cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
            endpoint.url = encrypt(url)

        if 'auth_token' in request.data:
            auth_token = request.data['auth_token'].strip()
            endpoint.auth_token = encrypt(auth_token) if auth_token else None

        if 'template' in request.data:
            endpoint.template = request.data['template']

        if 'events' in request.data:
            events = request.data['events']
            unknown = [e for e in events if e not in WebhookEndpoint.EVENTS]
            if unknown:
                return Response(
                    {'error': f'Unknown event types: {unknown}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            endpoint.events = events

        if 'is_active' in request.data:
            endpoint.is_active = bool(request.data['is_active'])

        endpoint.save()
        return Response(_serialize_endpoint(endpoint))

    def delete(self, request, pk, webhook_id):
        endpoint, err = self._get_endpoint(pk, webhook_id, request.user)
        if err:
            return err
        endpoint.delete()
        return Response({}, status=status.HTTP_200_OK)


class WebhookVerifyAPI(generics.GenericAPIView):

    def post(self, request, pk, webhook_id):
        project = _get_project_for_admin(pk, request.user)
        if not project:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            endpoint = project.webhooks.get(pk=webhook_id)
        except WebhookEndpoint.DoesNotExist:
            return Response({'error': 'Webhook not found'}, status=status.HTTP_404_NOT_FOUND)

        # Run synchronously so we can read the delivery result immediately.
        # Bypasses the subscription filter — verify always delivers regardless of subscribed events.
        from api.tasks import send_webhook
        send_webhook(
            endpoint_id=endpoint.pk,
            event_type='verify',
            payload={
                'event': 'verify',
                'message': 'This is a verification request from StringsRepository.',
                'actor': request.user.email,
            },
        )

        log = endpoint.logs.order_by('-delivered_at').first()

        if log and log.status_code and 200 <= log.status_code < 300:
            return Response({'status_code': log.status_code})

        if log and log.status_code:
            error_msg = _http_error_message(log.status_code, log.error)
        elif log and log.error:
            error_msg = _network_error_message(log.error)
        else:
            error_msg = 'No delivery attempt was recorded.'

        return Response({'error': error_msg}, status=status.HTTP_502_BAD_GATEWAY)


class WebhookLogsAPI(generics.GenericAPIView):

    def get(self, request, pk, webhook_id):
        project = _get_project_for_admin(pk, request.user)
        if not project:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            endpoint = project.webhooks.get(pk=webhook_id)
        except WebhookEndpoint.DoesNotExist:
            return Response({'error': 'Webhook not found'}, status=status.HTTP_404_NOT_FOUND)

        logs = endpoint.logs.all()[:50]
        data = [
            {
                'id': log.pk,
                'event_type': log.event_type,
                'status_code': log.status_code,
                'delivered_at': log.delivered_at.isoformat(),
                'error': log.error,
            }
            for log in logs
        ]
        return Response(data)


class WebhookEventsAPI(generics.GenericAPIView):
    """Returns the list of all supported event types."""

    def get(self, request, pk):
        return Response(WebhookEndpoint.EVENTS)
