import { PluralForms } from "./Translation"

interface TokenTranslation {
    translation: string
    code: string
    img?: string
    plural_forms?: PluralForms
    status: string
}

export default TokenTranslation