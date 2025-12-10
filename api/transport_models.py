class TranslationModel:

    def create(token, translation, comment=None, tags=None, code=None):
        model = TranslationModel()
        model.token = token
        model.translation = translation
        model.comment = comment
        model.tags = tags
        model.code = code
        return model

    def __init__(self, token_model=None, code=None):
        if token_model:
            self.token = token_model.token
            self.tags = [tag.tag for tag in token_model.tags.all()]

            translation = token_model.translation.filter(
                language__code=code.upper()).first()
            if translation:
                text = translation.translation
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
