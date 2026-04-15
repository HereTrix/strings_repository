import django_filters
from api.models.translations import StringToken
from django.db.models import Q


class TranslationTokenFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_query')
    tags = django_filters.CharFilter(method='filter_tags')
    status = django_filters.CharFilter(method='filter_status')

    def filter_query(self, queryset, name, value):
        print('filtering query', value)
        return queryset.filter(
            Q(translation__translation__icontains=value) |
            Q(token__icontains=value)
        )

    def filter_tags(self, queryset, name, value):
        for tag in value.split(','):
            queryset = queryset.filter(tags__tag=tag)
        return queryset

    def filter_status(self, queryset, name, value):
        code = self.request.resolver_match.kwargs.get('code', '').upper()
        return queryset.filter(
            translation__status=value,
            translation__language__code=code,
        )

    class Meta:
        model = StringToken
        fields = ['q', 'tags', 'status']
