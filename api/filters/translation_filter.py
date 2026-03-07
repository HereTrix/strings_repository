import django_filters
from api.models import StringToken
from django.db.models import Q


class TranslationTokenFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_query')
    tags = django_filters.CharFilter(method='filter_tags')
    untranslated = django_filters.BooleanFilter(method='filter_untranslated')
    status = django_filters.CharFilter(field_name='status')

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

    def filter_untranslated(self, queryset, name, value):
        print('filtering untranslated', value)
        if value:
            return queryset.filter(
                Q(translation__translation__exact='') |
                Q(translation__translation__isnull=True)
            )
        return queryset

    class Meta:
        model = StringToken
        fields = ['q', 'tags', 'untranslated', 'status']
