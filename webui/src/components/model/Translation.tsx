interface Translation {
    token: string
    translation: string | undefined
}

export interface TranslationModel {
    token: string
    translation: string | undefined
    tags: string[]
}

export default Translation