from django.test import TestCase

from api.file_processors.common import escape_quotes


class EscapeQuotesTestCase(TestCase):

    def test_plain_string_unchanged(self):
        self.assertEqual(escape_quotes('hello world'), 'hello world')

    def test_single_quote_escaped(self):
        result = escape_quotes("it's")
        self.assertIn("\\'", result)

    def test_already_escaped_not_doubled(self):
        original = "it\\'s"
        result = escape_quotes(original)
        self.assertEqual(result.count("\\'"), 1)

    def test_multiple_quotes(self):
        result = escape_quotes("don't won't")
        self.assertEqual(result.count("\\'"), 2)

    def test_empty_string(self):
        self.assertEqual(escape_quotes(''), '')
