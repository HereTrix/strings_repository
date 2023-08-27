import Language from "./Language"

export enum ProjectRole {
    owner, admin, editor, translator
}

interface Project {
    id: number
    name: string
    description: string | null
    languages: Language[]
    role: ProjectRole
}

export default Project