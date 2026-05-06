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
}

export default TokenTranslation
