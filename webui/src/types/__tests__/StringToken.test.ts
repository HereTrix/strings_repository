import StringToken, {
    getStatusName,
    getStatusVariant,
    STATUS_OPTIONS,
} from '../StringToken'

describe('STATUS_OPTIONS', () => {
    it('contains active and deprecated', () => {
        expect(STATUS_OPTIONS).toEqual(['active', 'deprecated'])
    })
})

describe('getStatusVariant', () => {
    it.each([
        ['active', 'success'],
        ['deprecated', 'danger'],
        ['unknown', 'info'],
        ['', 'info'],
    ])('"%s" → "%s"', (status, expected) => {
        expect(getStatusVariant(status)).toBe(expected)
    })
})

describe('getStatusName', () => {
    it.each([
        ['active', 'Active'],
        ['deprecated', 'Deprecated'],
        ['unknown', 'Unknown'],
        ['', 'Unknown'],
    ])('"%s" → "%s"', (status, expected) => {
        expect(getStatusName(status)).toBe(expected)
    })
})
