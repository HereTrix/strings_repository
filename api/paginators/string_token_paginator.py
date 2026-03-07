from rest_framework.pagination import LimitOffsetPagination, Response


class TranslationsPagination(LimitOffsetPagination):
    default_limit = 50
    max_limit = 200

    def get_paginated_response(self, data):
        return Response({
            'count': self.count,
            'results': data
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': {'type': 'integer'},
                'results': schema,
            }
        }
