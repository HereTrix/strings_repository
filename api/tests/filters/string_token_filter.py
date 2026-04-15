from django.test import TestCase

from api.filters.string_token_filter import StringTokenFilter
from api.models.tag import Tag
from api.tests.helpers import (
    make_language, make_project, make_token, make_translation, make_user,
)


class StringTokenFilterTestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.lang = make_language(self.project, 'EN')

        self.token_a = make_token(self.project, 'welcome_screen')
        make_translation(self.token_a, self.lang, 'Hello World')

        self.token_b = make_token(self.project, 'goodbye_screen')
        make_translation(self.token_b, self.lang, '')

        self.token_c = make_token(self.project, 'settings_title')
        # no translation for token_c

        from api.models.translations import StringToken
        self.qs = StringToken.objects.filter(project=self.project)

    def _apply(self, params):
        return StringTokenFilter(params, queryset=self.qs).qs.distinct()

    def test_filter_query_by_token_name(self):
        result = self._apply({'q': 'welcome'})
        self.assertIn(self.token_a, result)
        self.assertNotIn(self.token_b, result)

    def test_filter_query_by_translation_text(self):
        result = self._apply({'q': 'Hello'})
        self.assertIn(self.token_a, result)
        self.assertNotIn(self.token_b, result)

    def test_filter_query_case_insensitive(self):
        result = self._apply({'q': 'hello world'})
        self.assertIn(self.token_a, result)

    def test_filter_tags_single(self):
        tag, _ = Tag.objects.get_or_create(tag='ios')
        self.token_a.tags.add(tag)
        result = self._apply({'tags': 'ios'})
        self.assertIn(self.token_a, result)
        self.assertNotIn(self.token_b, result)

    def test_filter_tags_multiple_requires_all(self):
        tag1, _ = Tag.objects.get_or_create(tag='ios')
        tag2, _ = Tag.objects.get_or_create(tag='android')
        self.token_a.tags.add(tag1, tag2)
        self.token_b.tags.add(tag1)
        result = self._apply({'tags': 'ios,android'})
        self.assertIn(self.token_a, result)
        self.assertNotIn(self.token_b, result)

    def test_filter_untranslated_returns_empty_or_missing(self):
        result = self._apply({'untranslated': 'true'})
        # token_b has empty translation, token_c has no translation row
        self.assertIn(self.token_b, result)
        self.assertNotIn(self.token_a, result)

    def test_filter_new_returns_empty_or_missing(self):
        result = self._apply({'new': 'true'})
        self.assertIn(self.token_b, result)
        self.assertNotIn(self.token_a, result)

    def test_filter_status(self):
        self.token_a.status = 'deprecated'
        self.token_a.save()
        result = self._apply({'status': 'deprecated'})
        self.assertIn(self.token_a, result)
        self.assertNotIn(self.token_b, result)

    def test_no_filters_returns_all(self):
        result = self._apply({})
        self.assertIn(self.token_a, result)
        self.assertIn(self.token_b, result)
        self.assertIn(self.token_c, result)
