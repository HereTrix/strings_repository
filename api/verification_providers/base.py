class VerificationProvider:
    def verify(
        self,
        items: list[dict],
        checks: list[str],
        project_description: str,
        glossary_terms: list[dict] = (),
    ) -> list[dict]:
        """
        items: list of dicts with keys:
            token_id (int), token_key (str), language (str),
            plural_form (str|None), source (str), current (str),
            placeholders (list[str])
        checks: list of check key strings selected by user
        project_description: project description for context (may be empty string)
        glossary_terms: list of dicts with keys: term (str), case_sensitive (bool),
            preferred_translation (str — for the target language; may be empty string)

        Returns list of dicts with keys:
            token_id (int), plural_form (str|None),
            severity ('ok'|'warning'|'error'), suggestion (str), reason (str)
        """
        raise NotImplementedError

    def extract_glossary(
        self,
        strings: list[str],
        project_description: str,
    ) -> list[dict]:
        """
        strings: up to 200 source-language strings sampled from the project
        project_description: may be empty string

        Returns list of dicts: [{term, definition, translations: [{language_code, preferred_translation}]}]
        """
        raise NotImplementedError
