import django_filters
from api.models.translations import StringToken
from django.db.models import Q


class TranslationTokenFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_query')
    tags = django_filters.CharFilter(method='filter_tags')
    status = django_filters.CharFilter(method='filter_status')
    untranslated = django_filters.BooleanFilter(method='filter_untranslated')
    scope = django_filters.NumberFilter(field_name='scopes__id')

    def filter_query(self, queryset, name, value):
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

    def filter_untranslated(self, queryset, name, value):
        if value:
            code = self.request.resolver_match.kwargs.get('code', '').upper()
            return queryset.exclude(
                translation__language__code=code,
                translation__translation__gt='',
            )
        return queryset

    class Meta:
        model = StringToken
        fields = ['q', 'tags', 'status', 'untranslated', 'scope']
