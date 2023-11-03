from django.test import TestCase
from api.file_processors.strings_file import AppleStringsFileReader, AppleStringsFileWriter
from api.transport_models import TranslationModel


class AppleStringsTestCase(TestCase):

    def testStringsWriter(self):
        input = [
            TranslationModel.create('token', 'value', 'Some\ncomment'),
            TranslationModel.create('empty_comment', 'Empty comment value'),
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
            TranslationModel.create('token', 'value',
                                    'Some comment\nAnd another one'),
            TranslationModel.create('empty_comment', 'Empty comment value'),
        ]
        reader = AppleStringsFileReader()
        result = reader.read(input)
        self.assertEqual(result, expectation)
