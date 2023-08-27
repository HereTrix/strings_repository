from django.test import TestCase
from api.file_processors.strings_file import AppleStringsFileReader, AppleStringsFileWriter
from api.transport_models import TranslationModel


class AppleStringsTestCase(TestCase):

    def testStringsWriter(self):
        input = [
            TranslationModel('token', 'value', 'Some\ncomment'),
            TranslationModel('empty_comment', 'Empty comment value'),
        ]
        expectation = '''/*Some
comment*/
"token" = "value";
"empty_comment" = "Empty comment value";'''
        writer = AppleStringsFileWriter(input)
        result = writer.convert_file()
        self.assertEqual(result, expectation)

    def testStringsReader(self):
        input = '''/*Some comment*/
//And another one
"token" = "value";
"empty_comment" = "Empty comment value";'''
        expectation = [
            TranslationModel('token', 'value',
                             'Some comment\nAnd another one'),
            TranslationModel('empty_comment', 'Empty comment value'),
        ]
        reader = AppleStringsFileReader(input)
        result = reader.read()
        self.assertEqual(result, expectation)
