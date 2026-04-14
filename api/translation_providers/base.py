class TranslationProvider:
    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        raise NotImplementedError
