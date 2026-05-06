import { GlossaryHint, PluralForms } from "./Translation"

interface TokenTranslation {
    translation: string
    code: string
    img?: string
    is_default: boolean
    plural_forms?: PluralForms
    status: string
}

export interface TokenTranslationsResponse {
    translations: TokenTranslation[]
    glossary_hints: GlossaryHint[]
    default_translation?: string
    default_language?: string
}

export default TokenTranslation
