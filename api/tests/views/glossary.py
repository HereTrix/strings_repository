import io
import csv
from rest_framework.test import APITestCase

from api.models.project import ProjectRole
from api.tests.helpers import (
    make_user, make_project, add_role, make_language, authed_client,
    make_glossary_term, make_glossary_translation,
)


class GlossaryTermListCreateAPITests(APITestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.translator = make_user('translator')
        self.project = make_project(owner=self.owner)
        add_role(self.translator, self.project, ProjectRole.Role.translator)
        self.lang_de = make_language(self.project, 'DE')
        self.lang_fr = make_language(self.project, 'FR')
        self.owner_client = authed_client(self.owner)
        self.translator_client = authed_client(self.translator)

    def test_list_returns_empty_for_new_project(self):
        resp = self.translator_client.get(f'/api/project/{self.project.pk}/glossary')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_list_returns_terms_with_translations(self):
        term = make_glossary_term(self.project, term='Login', owner=self.owner)
        make_glossary_translation(term, language_code='DE', preferred_translation='Anmelden', user=self.owner)
        resp = self.owner_client.get(f'/api/project/{self.project.pk}/glossary')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['term'], 'Login')
        self.assertEqual(len(data[0]['translations']), 1)
        self.assertEqual(data[0]['translations'][0]['language_code'], 'DE')

    def test_create_requires_admin_role(self):
        resp = self.translator_client.post(
            f'/api/project/{self.project.pk}/glossary',
            {'term': 'Submit'},
            format='json'
        )
        self.assertEqual(resp.status_code, 403)

    def test_create_term_success(self):
        resp = self.owner_client.post(
            f'/api/project/{self.project.pk}/glossary',
            {
                'term': 'Submit',
                'definition': 'To send a form',
                'translations': [{'language_code': 'DE', 'preferred_translation': 'Absenden'}],
            },
            format='json'
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['term'], 'Submit')
        self.assertEqual(data['definition'], 'To send a form')
        self.assertEqual(len(data['translations']), 1)
        self.assertEqual(data['translations'][0]['preferred_translation'], 'Absenden')

    def test_create_duplicate_term_returns_409(self):
        make_glossary_term(self.project, term='Submit')
        resp = self.owner_client.post(
            f'/api/project/{self.project.pk}/glossary',
            {'term': 'submit'},
            format='json'
        )
        self.assertEqual(resp.status_code, 409)

    def test_create_term_skips_invalid_language_code(self):
        resp = self.owner_client.post(
            f'/api/project/{self.project.pk}/glossary',
            {
                'term': 'Submit',
                'translations': [{'language_code': 'XX', 'preferred_translation': 'Something'}],
            },
            format='json'
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['translations'], [])


class GlossaryTermDetailAPITests(APITestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.translator = make_user('translator')
        self.project = make_project(owner=self.owner)
        add_role(self.translator, self.project, ProjectRole.Role.translator)
        self.lang_de = make_language(self.project, 'DE')
        self.term = make_glossary_term(self.project, term='Login', owner=self.owner)
        make_glossary_translation(self.term, 'DE', 'Anmelden', self.owner)
        self.owner_client = authed_client(self.owner)
        self.translator_client = authed_client(self.translator)

    def test_get_term_any_role(self):
        resp = self.translator_client.get(f'/api/project/{self.project.pk}/glossary/{self.term.pk}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['term'], 'Login')

    def test_update_term(self):
        resp = self.owner_client.put(
            f'/api/project/{self.project.pk}/glossary/{self.term.pk}',
            {'term': 'Sign In', 'definition': 'Authentication action', 'translations': []},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['term'], 'Sign In')
        self.assertEqual(resp.json()['translations'], [])

    def test_update_term_conflict(self):
        make_glossary_term(self.project, term='Register')
        resp = self.owner_client.put(
            f'/api/project/{self.project.pk}/glossary/{self.term.pk}',
            {'term': 'register'},
            format='json'
        )
        self.assertEqual(resp.status_code, 409)

    def test_delete_term(self):
        resp = self.owner_client.delete(f'/api/project/{self.project.pk}/glossary/{self.term.pk}')
        self.assertEqual(resp.status_code, 204)
        from api.models.glossary import GlossaryTerm
        self.assertFalse(GlossaryTerm.objects.filter(pk=self.term.pk).exists())

    def test_delete_requires_admin(self):
        resp = self.translator_client.delete(f'/api/project/{self.project.pk}/glossary/{self.term.pk}')
        self.assertEqual(resp.status_code, 403)


class GlossaryExportAPITests(APITestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.lang_de = make_language(self.project, 'DE')
        self.lang_fr = make_language(self.project, 'FR')
        self.client_auth = authed_client(self.owner)

    def test_export_csv(self):
        term = make_glossary_term(self.project, term='Submit')
        make_glossary_translation(term, 'DE', 'Absenden', self.owner)
        make_glossary_translation(term, 'FR', 'Soumettre', self.owner)
        make_glossary_term(self.project, term='Cancel')
        resp = self.client_auth.get(f'/api/project/{self.project.pk}/glossary/export')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        content = resp.content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        expected_headers = {'term', 'definition', 'case_sensitive', 'language_code', 'preferred_translation'}
        self.assertEqual(set(reader.fieldnames), expected_headers)
        cancel_rows = [r for r in rows if r['term'] == 'Cancel']
        self.assertEqual(len(cancel_rows), 1)
        self.assertEqual(cancel_rows[0]['language_code'], '')
        submit_rows = [r for r in rows if r['term'] == 'Submit']
        self.assertEqual(len(submit_rows), 2)


class GlossaryImportAPITests(APITestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.translator = make_user('translator')
        self.project = make_project(owner=self.owner)
        add_role(self.translator, self.project, ProjectRole.Role.translator)
        self.lang_de = make_language(self.project, 'DE')
        self.owner_client = authed_client(self.owner)
        self.translator_client = authed_client(self.translator)

    def _make_csv(self, rows):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['term', 'definition', 'case_sensitive', 'language_code', 'preferred_translation'])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        output.seek(0)
        return io.BytesIO(output.getvalue().encode('utf-8'))

    def test_import_creates_terms(self):
        csv_data = self._make_csv([
            {'term': 'Login', 'definition': '', 'case_sensitive': 'false', 'language_code': 'DE', 'preferred_translation': 'Anmelden'},
            {'term': 'Logout', 'definition': '', 'case_sensitive': 'false', 'language_code': '', 'preferred_translation': ''},
        ])
        resp = self.owner_client.post(
            f'/api/project/{self.project.pk}/glossary/import',
            {'file': csv_data},
            format='multipart'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['imported'], 2)
        self.assertEqual(data['updated'], 0)
        self.assertEqual(data['skipped'], 0)

    def test_import_updates_existing(self):
        make_glossary_term(self.project, term='Login', definition='Old def')
        csv_data = self._make_csv([
            {'term': 'login', 'definition': 'New def', 'case_sensitive': 'false', 'language_code': '', 'preferred_translation': ''},
        ])
        resp = self.owner_client.post(
            f'/api/project/{self.project.pk}/glossary/import',
            {'file': csv_data},
            format='multipart'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['updated'], 1)
        self.assertEqual(data['imported'], 0)
        from api.models.glossary import GlossaryTerm
        updated = GlossaryTerm.objects.get(project=self.project, term__iexact='Login')
        self.assertEqual(updated.definition, 'New def')

    def test_import_skips_unknown_language(self):
        csv_data = self._make_csv([
            {'term': 'Submit', 'definition': '', 'case_sensitive': 'false', 'language_code': 'XX', 'preferred_translation': 'Something'},
        ])
        resp = self.owner_client.post(
            f'/api/project/{self.project.pk}/glossary/import',
            {'file': csv_data},
            format='multipart'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(len(data['warnings']) > 0)
        self.assertIn('XX', data['warnings'][0])

    def test_import_requires_admin(self):
        csv_data = self._make_csv([{'term': 'Test', 'definition': '', 'case_sensitive': 'false', 'language_code': '', 'preferred_translation': ''}])
        resp = self.translator_client.post(
            f'/api/project/{self.project.pk}/glossary/import',
            {'file': csv_data},
            format='multipart'
        )
        self.assertEqual(resp.status_code, 403)
