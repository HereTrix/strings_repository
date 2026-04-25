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

// Pseudo-status used only as a UI filter — not a real translation status value
export const UNTRANSLATED_FILTER = 'untranslated'

export const getStatusName = (status: string) => {
    switch (status) {
        case 'new': return 'New'
        case 'in_review': return 'In Review'
        case 'approved': return 'Approved'
        case 'deprecated': return 'Deprecated'
        case UNTRANSLATED_FILTER: return 'Untranslated'
        default: return status
    }
}

export const getStatusVariant = (status: string): string => {
    switch (status) {
        case 'new': return 'primary'
        case 'in_review': return 'warning'
        case 'approved': return 'success'
        case 'deprecated': return 'secondary'
        case UNTRANSLATED_FILTER: return 'danger'
        default: return 'info'
    }
}

export default Translation
