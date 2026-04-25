import { useCallback, useState } from "react"
import PaginatedResponse from "../types/PaginatedResponse"

export const PAGE_LIMIT = 20

export function usePagination<T>() {
    const [items, setItems] = useState<T[]>([])
    const [offset, setOffset] = useState(0)
    const [hasMore, setHasMore] = useState(true)
    const [total, setTotal] = useState(0)

    const handleResponse = useCallback((response: PaginatedResponse<T>, pageOffset: number) => {
        setHasMore(response.results.length >= PAGE_LIMIT)
        setTotal(response.count)
        if (pageOffset === 0) {
            setItems(response.results)
        } else {
            setItems(prev => [...prev, ...response.results])
        }
        setOffset(pageOffset)
    }, [])

    return { items, offset, hasMore, setHasMore, total, handleResponse, setItems }
}
