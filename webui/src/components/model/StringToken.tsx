interface StringToken {
    id: string
    token: string
    comment: string | undefined
    tags: string[] | undefined
    status: string
}

export const STATUS_OPTIONS = ['active', 'deprecated']

export const getStatusVariant = (status: string): string => {
    switch (status) {
        case 'active': return 'success'
        case 'deprecated': return 'danger'
        default: return 'info'
    }
}

export const getStatusName = (status: string): string => {
    switch (status) {
        case 'active': return 'Active'
        case 'deprecated': return 'Deprecated'
        default: return 'Unknown'
    }
}

export default StringToken