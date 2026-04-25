export interface Bundle {
    id: number
    version_name: string
    is_active: boolean
    created_at: string
    created_by: string | null
    translation_count: number
}

export interface BundleDiffEntry {
    token: string
    language: string
    value?: string
    from?: string
    to?: string
}

export interface BundleDiff {
    added: BundleDiffEntry[]
    removed: BundleDiffEntry[]
    changed: BundleDiffEntry[]
    unchanged_count: number
    new_tokens: string[]
    deleted_tokens: string[]
}
