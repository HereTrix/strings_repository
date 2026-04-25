import {
    getStatusName,
    getStatusVariant,
    STATUS_OPTIONS,
    EDITABLE_STATUSES,
    UNTRANSLATED_FILTER,
    PLURAL_FORM_ORDER,
} from '../Translation'

describe('STATUS_OPTIONS', () => {
    it('starts with new', () => {
        expect(STATUS_OPTIONS[0]).toBe('new')
    })

    it('includes all editable statuses', () => {
        expect(STATUS_OPTIONS).toEqual(expect.arrayContaining(EDITABLE_STATUSES))
    })
})

describe('EDITABLE_STATUSES', () => {
    it('does not include new', () => {
        expect(EDITABLE_STATUSES).not.toContain('new')
    })

    it('contains in_review, approved, deprecated', () => {
        expect(EDITABLE_STATUSES).toEqual(['in_review', 'approved', 'deprecated'])
    })
})

describe('PLURAL_FORM_ORDER', () => {
    it('contains all six CLDR forms in correct order', () => {
        expect(PLURAL_FORM_ORDER).toEqual(['zero', 'one', 'two', 'few', 'many', 'other'])
    })
})

describe('getStatusName', () => {
    it.each([
        ['new', 'New'],
        ['in_review', 'In Review'],
        ['approved', 'Approved'],
        ['deprecated', 'Deprecated'],
        [UNTRANSLATED_FILTER, 'Untranslated'],
        ['unknown', 'unknown'],
    ])('"%s" → "%s"', (status, expected) => {
        expect(getStatusName(status)).toBe(expected)
    })
})

describe('getStatusVariant', () => {
    it.each([
        ['new', 'primary'],
        ['in_review', 'warning'],
        ['approved', 'success'],
        ['deprecated', 'secondary'],
        [UNTRANSLATED_FILTER, 'danger'],
        ['unknown', 'info'],
    ])('"%s" → "%s"', (status, expected) => {
        expect(getStatusVariant(status)).toBe(expected)
    })
})
