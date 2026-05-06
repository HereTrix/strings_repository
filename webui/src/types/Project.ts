import Language from "./Language"

export enum ProjectRole {
    owner = 'owner',
    admin = 'admin',
    editor = 'editor',
    translator = 'translator'
}

interface Project {
    id: number
    name: string
    description: string | null
    languages: Language[]
    role: ProjectRole
    require_2fa: boolean
    has_ai_provider: boolean
    verification_cap?: number
    has_glossary_terms: boolean
}

export default Project
