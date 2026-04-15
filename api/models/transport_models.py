class TranslationModel:

    def create(token, translation, comment=None, tags=None, code=None, plural_forms=None):
        model = TranslationModel()
        model.token = token
        model.translation = translation
        model.comment = comment
        model.tags = tags
        model.code = code
        model.plural_forms = plural_forms or {}
        return model

    @classmethod
    def from_bundle_map(cls, bundle_map):
        """Build a TranslationModel from a TranslationBundleMap row.

        Expects bundle_map to have select_related('token', 'language')
        and prefetch_related('token__tags') already applied.
        """
        m = cls()
        string_token = bundle_map.token
        m.token = string_token.token
        m.comment = string_token.comment
        m.tags = [tag.tag for tag in string_token.tags.all()]
        m.translation = bundle_map.value
        m.code = bundle_map.language.code.lower()
        m.plural_forms = {}
        return m

    def __init__(self, token_model=None, code=None):
        self.plural_forms = {}
        if token_model:
            self.token = token_model.token
            self.tags = [tag.tag for tag in token_model.tags.all()]

            translation = token_model.translation.filter(
                language__code=code.upper()).first()
            if translation:
                text = translation.translation
                self.plural_forms = {
                    pf.plural_form: pf.value
                    for pf in translation.plural_forms.all()
                }
            else:
                text = ''

            self.translation = text
            self.comment = token_model.comment
            self.code = code

    def __eq__(self, other):
        if not isinstance(other, TranslationModel):
            return NotImplemented

        return self.token == other.token and self.translation == other.translation and self.comment == other.comment

    def __str__(self) -> str:
        return f'{self.token} {self.translation}'


class APIProject:

    def __init__(self, project, languages, role) -> None:
        self.id = project.id
        self.name = project.name
        self.description = project.description
        self.languages = languages
        self.role = role
