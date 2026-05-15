# AI Translation Verification

AI verification runs quality audits on your translations using any OpenAI-compatible or Anthropic-compatible provider (including self-hosted models via a custom endpoint URL). The provider is configured per-project in **Project → Info → AI Provider**.

## Modes

| Mode                    | What is checked                                                                                                                                                          | Target language required |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| **Source Quality**      | Source/default language strings for spelling, grammar, tone, punctuation, capitalisation, and placeholder format                                                         | No                       |
| **Translation Accuracy** | Translations from the source language to a selected target language for semantic accuracy, placeholder preservation, omissions/additions, grammar, and tone match       | Yes                      |

## How it works

1. **Configure an AI provider** — go to **Project → Info → AI Provider**, select a provider type (OpenAI-compatible or Anthropic-compatible), enter the model name and API key. Leave the endpoint URL blank to use the default. Built-in presets are available for OpenAI, Claude, and Ollama.
2. **Run a verification** — in the **Verify** tab, click **Run Verification**. Select a mode, optionally filter by scope, tags, or "new only" (Mode 2), choose which checks to include, and click **Estimate strings** to preview API token usage before submitting.
3. **Review results** — the job runs asynchronously; the tab polls for status every 5 seconds. Each result row shows a severity badge (`ok` / `warning` / `error`), a word-level diff of the current value vs. the AI suggestion, and the reason.
4. **Apply suggestions** — editors, admins, and owners can select individual suggestions, adjust the text inline, and apply them as standard translation updates with full history tracking. Applying any suggestion marks the report read-only.
5. **Comment** — any project member can add comments to individual suggestions for discussion.

Reports are capped per project (default: 10; configurable by the project owner). When the cap is reached, the oldest report is deleted automatically. Admins and owners can delete any report manually. A `verification.completed` webhook event fires when each job finishes.
