interface StringToken {
    id: string
    token: string
    comment: string | undefined
    tags: string[] | undefined
    status: string
}

export const STATUS_OPTIONS = ['active', 'deprecated']

export default StringToken