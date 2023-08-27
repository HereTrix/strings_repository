class TranslationModel:

    def __init__(self, token, translation, comment=None):
        self.token = token
        self.translation = translation
        self.comment = comment

    def __init__(self, token_model, code):
        self.token = token_model.token

        translation = token_model.translation.filter(
            language__code=code.upper()).first()
        if translation:
            text = translation.translation
        else:
            text = ''

        self.translation = text
        self.comment = token_model.comment

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
