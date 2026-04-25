interface Language {
    code: string
    name: string
    img?: string
    is_default?: boolean
}

export interface LanguageProgress {
    translated: number
    total: number
    percent: number
}

export default Language
