class VerificationProvider:
    def verify(
        self,
        items: list[dict],
        checks: list[str],
        project_description: str,
    ) -> list[dict]:
        """
        items: list of dicts with keys:
            token_id (int), token_key (str), language (str),
            plural_form (str|None), source (str), current (str),
            placeholders (list[str])
        checks: list of check key strings selected by user
        project_description: project description for context (may be empty string)

        Returns list of dicts with keys:
            token_id (int), plural_form (str|None),
            severity ('ok'|'warning'|'error'), suggestion (str), reason (str)
        """
        raise NotImplementedError
