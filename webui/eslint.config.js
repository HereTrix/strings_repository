import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
    js.configs.recommended,
    ...tseslint.configs.recommended,
    {
        plugins: {
            react: reactPlugin,
            "react-hooks": reactHooks,
        },

        languageOptions: {
            globals: {
                ...globals.browser,
            },
        },

        linterOptions: {
            reportUnusedDisableDirectives: "error",
        },
    },
    globalIgnores([
        "static/**",
        "node_modules/**",
        "__mocks__/**",
        "webpack.config.js",
        "jest.config.js"
    ]),
]);