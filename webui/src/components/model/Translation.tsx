interface Translation {
    token: string
    translation: string | undefined
}

export type PluralForms = Partial<Record<'zero' | 'one' | 'two' | 'few' | 'many' | 'other', string>>

export interface TranslationModel {
    token: string
    translation: string | undefined
    tags: string[]
    status: string
    plural_forms?: PluralForms
    default_translation?: string
}

export const PLURAL_FORM_ORDER: Array<keyof PluralForms> = ['zero', 'one', 'two', 'few', 'many', 'other']

// Status can be 'new' but it can not be set by the user, so it's not included in the options
export const EDITABLE_STATUSES = ['in_review', 'approved', 'deprecated']
export const STATUS_OPTIONS = ['new', ...EDITABLE_STATUSES]

export const getStatusName = (status: string) => {
    switch (status) {
        case 'new':
            return 'New'
        case 'in_review':
            return 'In Review'
        case 'approved':
            return 'Approved'
        case 'deprecated':
            return 'Deprecated'
        default:
            return status
    }
}

export const getStatusVariant = (status: string): string => {
    switch (status) {
        case 'new': return 'primary'
        case 'in_review': return 'warning'
        case 'approved': return 'success'
        case 'deprecated': return 'secondary'
        default: return 'info'
    }
}

export default Translation