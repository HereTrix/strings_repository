import django_filters
from api.models.translations import StringToken
from django.db.models import Q


class StringTokenFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_query')
    tags = django_filters.CharFilter(method='filter_tags')
    new = django_filters.BooleanFilter(method='filter_new')
    untranslated = django_filters.BooleanFilter(method='filter_untranslated')
    status = django_filters.CharFilter(field_name='translation__status')

    def filter_query(self, queryset, name, value):
        return queryset.filter(
            Q(token__icontains=value) |
            Q(translation__translation__icontains=value)
        )

    def filter_tags(self, queryset, name, value):
        for tag in value.split(','):
            queryset = queryset.filter(tags__tag=tag)
        return queryset

    def filter_new(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(translation__translation__exact='') |
                Q(translation__translation__isnull=True)
            )
        return queryset

    def filter_untranslated(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(translation__translation__exact='') |
                Q(translation__translation__isnull=True)
            )
        return queryset

    class Meta:
        model = StringToken
        fields = ['q', 'tags', 'new', 'untranslated', 'status']
