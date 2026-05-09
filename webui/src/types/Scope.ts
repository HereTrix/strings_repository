// Copyright (c) StringsRepository Contributors
// SPDX-License-Identifier: MIT

export interface ScopeImage {
    id: number
    url: string
    created_at: string
}

interface Scope {
    id: number
    name: string
    description: string
    images: ScopeImage[]
    token_count: number
    token_ids: number[]
}

export default Scope
