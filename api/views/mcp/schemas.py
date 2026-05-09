# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

TOOLS = [
    {
        "name": "get_project",
        "description": "Get the project associated with the configured access token.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_languages",
        "description": "List all language codes configured for the project.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_tokens",
        "description": "List localization keys in the project with optional filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Filter by key name or translation text"},
                "tags": {"type": "string", "description": "Comma-separated tag names to filter by"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "get_token",
        "description": "Get a localization key with all its translations across every language.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token_key": {"type": "string", "description": "The key name, e.g. 'onboarding.title'"},
            },
            "required": ["token_key"],
        },
    },
    {
        "name": "create_token",
        "description": "Create a new localization key. Returns an error if the key already exists.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token_key": {"type": "string"},
                "comment": {"type": "string", "default": ""},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tag names to attach",
                },
            },
            "required": ["token_key"],
        },
    },
    {
        "name": "set_translation",
        "description": "Create or update a translation for a key in a given language.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token_key": {"type": "string"},
                "language_code": {"type": "string", "description": "Language code, e.g. 'EN' or 'FR'"},
                "text": {"type": "string"},
            },
            "required": ["token_key", "language_code", "text"],
        },
    },
    {
        "name": "search_similar_tokens",
        "description": "Search for existing keys whose name or translations resemble the given text. Use this to avoid creating duplicates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["text"],
        },
    },
    {
        "name": "suggest_token_key",
        "description": "Suggest a key name derived from source text following common naming conventions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_text": {"type": "string"},
                "existing_tokens": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Already-used key names, to avoid collisions",
                },
            },
            "required": ["source_text"],
        },
    },
    {
        "name": "get_token_naming_patterns",
        "description": "Analyse a sample of existing keys to infer this project's naming conventions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sample_size": {"type": "integer", "default": 50},
            },
            "required": [],
        },
    },
    {
        "name": "batch_create_tokens",
        "description": "Create multiple localization keys with default-language translations in one call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "token_key": {"type": "string"},
                            "comment": {"type": "string"},
                            "language_code": {"type": "string"},
                            "text": {"type": "string"},
                        },
                        "required": ["token_key"],
                    },
                },
            },
            "required": ["entries"],
        },
    },
    {
        "name": "check_glossary",
        "description": "Check whether any words or phrases in a source string match project glossary terms. Returns matched terms with their definitions and preferred translations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_text": {
                    "type": "string",
                    "description": "The source string to check against the glossary",
                },
                "language_code": {
                    "type": "string",
                    "description": "Optional target language code (e.g. 'DE'). When provided, includes preferred_translation for that language.",
                },
            },
            "required": ["source_text"],
        },
    },
    {
        "name": "suggest_translation",
        "description": "Return translation memory suggestions: previously-translated strings with source text similar to the given source_text, translated into the specified language.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_text": {"type": "string"},
                "language_code": {
                    "type": "string",
                    "description": "Target language code, e.g. 'DE'",
                },
            },
            "required": ["source_text", "language_code"],
        },
    },
    {
        "name": "verify_string",
        "description": (
            "Run AI quality verification on a single source/translation pair. "
            "Requires the project to have an AI provider configured. "
            "Returns severity ('ok', 'warning', or 'error'), a suggested correction, and the reason. "
            "Note: response time depends on the AI provider (may take several seconds)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_text": {
                    "type": "string",
                    "description": "The source (default-language) string",
                },
                "translation_text": {
                    "type": "string",
                    "description": "The translation to verify",
                },
                "language_code": {
                    "type": "string",
                    "description": "The target language code, e.g. 'DE'",
                },
                "checks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional list of check keys to run. "
                        "Defaults to all translation_accuracy checks. "
                        "Valid values: semantic_accuracy, placeholder_preservation, "
                        "omissions_additions, grammar_target, tone_match."
                    ),
                },
            },
            "required": ["source_text", "translation_text", "language_code"],
        },
    },
]
