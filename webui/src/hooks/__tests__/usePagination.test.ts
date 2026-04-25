import { renderHook, act } from '@testing-library/react'
import { usePagination, PAGE_LIMIT } from '../usePagination'

const makeResponse = (count: number, results: number[]) => ({ count, results })

describe('usePagination', () => {
    it('starts empty with hasMore true', () => {
        const { result } = renderHook(() => usePagination<number>())
        expect(result.current.items).toEqual([])
        expect(result.current.hasMore).toBe(true)
        expect(result.current.total).toBe(0)
        expect(result.current.offset).toBe(0)
    })

    it('sets items and total on first page', () => {
        const { result } = renderHook(() => usePagination<number>())
        const items = Array.from({ length: PAGE_LIMIT }, (_, i) => i)

        act(() => { result.current.handleResponse(makeResponse(50, items), 0) })

        expect(result.current.items).toEqual(items)
        expect(result.current.total).toBe(50)
        expect(result.current.offset).toBe(0)
    })

    it('sets hasMore false when results fewer than PAGE_LIMIT', () => {
        const { result } = renderHook(() => usePagination<number>())

        act(() => { result.current.handleResponse(makeResponse(5, [1, 2, 3, 4, 5]), 0) })

        expect(result.current.hasMore).toBe(false)
    })

    it('keeps hasMore true when results equal PAGE_LIMIT', () => {
        const { result } = renderHook(() => usePagination<number>())
        const full = Array.from({ length: PAGE_LIMIT }, (_, i) => i)

        act(() => { result.current.handleResponse(makeResponse(100, full), 0) })

        expect(result.current.hasMore).toBe(true)
    })

    it('appends items on subsequent pages', () => {
        const { result } = renderHook(() => usePagination<number>())
        const page1 = Array.from({ length: PAGE_LIMIT }, (_, i) => i)
        const page2 = Array.from({ length: 5 }, (_, i) => PAGE_LIMIT + i)

        act(() => { result.current.handleResponse(makeResponse(25, page1), 0) })
        act(() => { result.current.handleResponse(makeResponse(25, page2), PAGE_LIMIT) })

        expect(result.current.items).toEqual([...page1, ...page2])
        expect(result.current.offset).toBe(PAGE_LIMIT)
    })

    it('replaces items when offset is 0 (refresh)', () => {
        const { result } = renderHook(() => usePagination<number>())

        act(() => { result.current.handleResponse(makeResponse(3, [1, 2, 3]), 0) })
        act(() => { result.current.handleResponse(makeResponse(2, [10, 20]), 0) })

        expect(result.current.items).toEqual([10, 20])
        expect(result.current.total).toBe(2)
    })

    it('setHasMore overrides pagination state', () => {
        const { result } = renderHook(() => usePagination<number>())

        act(() => { result.current.setHasMore(false) })

        expect(result.current.hasMore).toBe(false)
    })
})
