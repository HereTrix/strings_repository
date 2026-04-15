from unittest.mock import MagicMock

from django.test import TestCase

from api.filters.translation_filter import TranslationTokenFilter
from api.tests.helpers import make_language, make_project, make_token, make_translation, make_user


def _mock_request(code='EN'):
    request = MagicMock()
    request.resolver_match.kwargs = {'code': code}
    return request


class TranslationTokenFilterTestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.lang_en = make_language(self.project, 'EN')
        self.lang_de = make_language(self.project, 'DE')

        self.token_a = make_token(self.project, 'welcome')
        self.token_b = make_token(self.project, 'farewell')
        self.token_c = make_token(self.project, 'settings')

        make_translation(self.token_a, self.lang_en, 'Hello')
        make_translation(self.token_b, self.lang_en, '')    # empty translation
        # token_c has no EN translation at all

        from api.models.translations import StringToken
        self.qs = StringToken.objects.filter(project=self.project)

    def _apply(self, params, code='EN'):
        return TranslationTokenFilter(
            params, queryset=self.qs, request=_mock_request(code)
        ).qs.distinct()

    def test_filter_untranslated_excludes_translated(self):
        result = self._apply({'untranslated': 'true'})
        self.assertNotIn(self.token_a, result)

    def test_filter_untranslated_includes_empty_translation(self):
        result = self._apply({'untranslated': 'true'})
        self.assertIn(self.token_b, result)

    def test_filter_untranslated_includes_missing_translation(self):
        result = self._apply({'untranslated': 'true'})
        self.assertIn(self.token_c, result)

    def test_filter_untranslated_is_language_scoped(self):
        # token_a has EN translation, but no DE translation
        result = self._apply({'untranslated': 'true'}, code='DE')
        self.assertIn(self.token_a, result)

    def test_filter_untranslated_false_returns_all(self):
        result = self._apply({'untranslated': 'false'})
        self.assertIn(self.token_a, result)
        self.assertIn(self.token_b, result)
        self.assertIn(self.token_c, result)

    def test_filter_status_by_language(self):
        from api.models.translations import Translation
        Translation.objects.filter(token=self.token_a, language=self.lang_en).update(status='approved')
        result = self._apply({'status': 'approved'})
        self.assertIn(self.token_a, result)
        self.assertNotIn(self.token_b, result)

    def test_filter_status_does_not_cross_languages(self):
        # Give token_a an approved DE translation, but filter on EN — should not appear
        make_translation(self.token_a, self.lang_de, 'Hallo')
        from api.models.translations import Translation
        Translation.objects.filter(token=self.token_a, language=self.lang_de).update(status='approved')
        result = self._apply({'status': 'approved'}, code='EN')
        self.assertNotIn(self.token_a, result)

    def test_filter_query_by_token_name(self):
        result = self._apply({'q': 'welcome'})
        self.assertIn(self.token_a, result)
        self.assertNotIn(self.token_b, result)

    def test_filter_query_by_translation_text(self):
        result = self._apply({'q': 'Hello'})
        self.assertIn(self.token_a, result)
        self.assertNotIn(self.token_b, result)

    def test_no_filters_returns_all(self):
        result = self._apply({})
        self.assertIn(self.token_a, result)
        self.assertIn(self.token_b, result)
        self.assertIn(self.token_c, result)
