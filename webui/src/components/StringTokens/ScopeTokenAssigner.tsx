import { FC, useCallback, useEffect, useRef, useState } from "react"
import { Button, Col, Form, Row, Spinner } from "react-bootstrap"
import InfiniteScroll from "react-infinite-scroll-component"
import TagFilter from "../UI/TagFilter"
import { APIMethod, http } from "../../utils/network"
import Scope from "../../types/Scope"
import StringToken from "../../types/StringToken"
import PaginatedResponse from "../../types/PaginatedResponse"
import ErrorAlert from "../UI/ErrorAlert"

type Props = {
    projectId: number
    scope: Scope
    onUpdate: () => void
}

const BATCH = 20

const ScopeTokenAssigner: FC<Props> = ({ projectId, scope, onUpdate }) => {
    const [assignedIds, setAssignedIds] = useState<Set<number>>(new Set(scope.token_ids))

    const [availQuery, setAvailQuery]     = useState('')
    const [availItems, setAvailItems]     = useState<StringToken[]>([])
    const [availOffset, setAvailOffset]   = useState(0)
    const [availHasMore, setAvailHasMore] = useState(false)
    const [availLoading, setAvailLoading] = useState(false)

    const [assignedQuery, setAssignedQuery]     = useState('')
    const [assignedItems, setAssignedItems]     = useState<StringToken[]>([])
    const [assignedOffset, setAssignedOffset]   = useState(0)
    const [assignedHasMore, setAssignedHasMore] = useState(false)

    const [selectedTags, setSelectedTags] = useState<string[]>([])
    const [projectTags, setProjectTags]   = useState<string[]>([])

    const [error, setError] = useState<string>()

    // Stable container IDs so InfiniteScroll can find its scrollable parent
    const instanceId = useRef(`sta-${scope.id}-${Math.random().toString(36).slice(2)}`)
    const availId    = `${instanceId.current}-avail`
    const assignedId = `${instanceId.current}-assigned`

    // ── fetchers ─────────────────────────────────────────────────────────────

    const fetchAvailable = useCallback(async (q: string, offset: number) => {
        if (offset === 0) setAvailLoading(true)
        const params: Record<string, any> = { q, limit: BATCH, offset }
        if (selectedTags.length) params.tags = selectedTags
        const result = await http<PaginatedResponse<StringToken>>({
            method: APIMethod.get,
            path: `/api/project/${projectId}/tokens`,
            params,
        })
        if (offset === 0) setAvailLoading(false)
        if (result.value) {
            const { results, count } = result.value
            const next = offset + results.length
            setAvailItems(prev => offset === 0 ? results : [...prev, ...results])
            setAvailOffset(next)
            setAvailHasMore(next < count)
        }
    }, [projectId, selectedTags])

    const fetchAssigned = useCallback(async (q: string, offset: number) => {
        const params: Record<string, any> = { scope: scope.id, q, limit: BATCH, offset }
        if (selectedTags.length) params.tags = selectedTags
        const result = await http<PaginatedResponse<StringToken>>({
            method: APIMethod.get,
            path: `/api/project/${projectId}/tokens`,
            params,
        })
        if (result.value) {
            const { results, count } = result.value
            const next = offset + results.length
            setAssignedItems(prev => offset === 0 ? results : [...prev, ...results])
            setAssignedOffset(next)
            setAssignedHasMore(next < count)
        }
    }, [projectId, scope.id, selectedTags])

    // ── fetch project tags once ───────────────────────────────────────────────

    useEffect(() => {
        http<string[]>({ method: APIMethod.get, path: `/api/project/${projectId}/tags` })
            .then(r => { if (r.value) setProjectTags(r.value) })
    }, [projectId])

    // ── reset + initial load when scope changes ───────────────────────────────

    useEffect(() => {
        setAssignedIds(new Set(scope.token_ids))
        setAvailQuery('')
        setAssignedQuery('')
        setAvailItems([])
        setAvailOffset(0)
        setAvailHasMore(false)
        setAssignedOffset(0)
        fetchAssigned('', 0)
    }, [scope.id]) // eslint-disable-line react-hooks/exhaustive-deps

    // ── debounced search for available ────────────────────────────────────────

    useEffect(() => {
        const ms = availQuery ? 300 : 0
        const t = setTimeout(() => fetchAvailable(availQuery, 0), ms)
        return () => clearTimeout(t)
    }, [availQuery, scope.id, selectedTags, fetchAvailable])

    // ── debounced search for assigned ─────────────────────────────────────────

    useEffect(() => {
        const ms = assignedQuery ? 300 : 0
        const t = setTimeout(() => fetchAssigned(assignedQuery, 0), ms)
        return () => clearTimeout(t)
    }, [assignedQuery, scope.id, selectedTags, fetchAssigned])

    // ── visible available = fetched minus already assigned ───────────────────

    const visibleAvail = availItems.filter(t => !assignedIds.has(Number(t.id)))

    // Auto-fetch more available items if too few are visible after filtering
    // (e.g. many results in the current page were already assigned)
    useEffect(() => {
        if (availHasMore && !availLoading && availItems.length > 0 && visibleAvail.length < 5) {
            fetchAvailable(availQuery, availOffset)
        }
    }, [visibleAvail.length]) // eslint-disable-line react-hooks/exhaustive-deps

    // ── add / remove ─────────────────────────────────────────────────────────

    const addToken = async (token: StringToken) => {
        const id = Number(token.id)
        setAssignedIds(prev => new Set([...prev, id]))
        setAssignedItems(prev => [token, ...prev])
        const result = await http({
            method: APIMethod.post,
            path: `/api/project/${projectId}/scopes/${scope.id}/tokens`,
            data: { token_ids: [id] },
        })
        if (result.error) {
            setAssignedIds(prev => { const s = new Set(prev); s.delete(id); return s })
            setAssignedItems(prev => prev.filter(t => Number(t.id) !== id))
            setError(result.error)
        } else {
            onUpdate()
        }
    }

    const removeToken = async (token: StringToken) => {
        const id = Number(token.id)
        setAssignedIds(prev => { const s = new Set(prev); s.delete(id); return s })
        setAssignedItems(prev => prev.filter(t => Number(t.id) !== id))
        const result = await http({
            method: APIMethod.delete,
            path: `/api/project/${projectId}/scopes/${scope.id}/tokens`,
            data: { token_ids: [id] },
        })
        if (result.error) {
            setAssignedIds(prev => new Set([...prev, id]))
            setAssignedItems(prev => [token, ...prev])
            setError(result.error)
        } else {
            onUpdate()
        }
    }

    // ── render ────────────────────────────────────────────────────────────────

    const panelStyle: React.CSSProperties = {
        height: 280,
        overflowY: 'auto',
        border: '1px solid #dee2e6',
        borderRadius: 4,
    }

    const rowStyle: React.CSSProperties = { borderBottom: '1px solid #f0f0f0' }

    const renderRow = (t: StringToken, action: 'add' | 'remove') => (
        <div key={t.id} className="d-flex align-items-center px-2 py-1" style={rowStyle}>
            <div className="flex-grow-1 overflow-hidden me-2">
                <code className="small d-block text-truncate">{t.token}</code>
                {t.comment && (
                    <span className="text-muted d-block text-truncate" style={{ fontSize: '0.7rem' }}>
                        {t.comment}
                    </span>
                )}
            </div>
            <Button
                size="sm"
                variant={action === 'add' ? 'outline-primary' : 'outline-danger'}
                style={{ flexShrink: 0, padding: '1px 8px', lineHeight: '1.4' }}
                onClick={() => action === 'add' ? addToken(t) : removeToken(t)}
            >
                {action === 'add' ? '+' : '×'}
            </Button>
        </div>
    )

    const loader = <div className="text-center py-2 text-muted small">Loading…</div>

    return (
        <>
            {projectTags.length > 0 && (
                <div className="mb-2">
                    <TagFilter
                        id={`${instanceId.current}-tags`}
                        tags={projectTags}
                        selected={selectedTags}
                        onChange={setSelectedTags}
                        placeholder="Filter by tag…"
                        size="sm"
                    />
                </div>
            )}
            <Row className="g-3">
                {/* ── Available ─────────────────────────────────────────── */}
                <Col xs={6}>
                    <div className="small fw-semibold mb-1 text-muted d-flex align-items-center gap-2">
                        Available
                        {availLoading && <Spinner size="sm" />}
                    </div>
                    <Form.Control
                        size="sm"
                        placeholder="Search keys…"
                        value={availQuery}
                        onChange={e => setAvailQuery(e.target.value)}
                        className="mb-1"
                    />
                    <div id={availId} style={panelStyle}>
                        {visibleAvail.length === 0 && !availLoading ? (
                            <div className="text-muted small text-center py-3">
                                {availQuery ? 'No results' : 'Type to search keys'}
                            </div>
                        ) : (
                            <InfiniteScroll
                                dataLength={visibleAvail.length}
                                next={() => fetchAvailable(availQuery, availOffset)}
                                hasMore={availHasMore}
                                loader={loader}
                                scrollableTarget={availId}
                            >
                                {visibleAvail.map(t => renderRow(t, 'add'))}
                            </InfiniteScroll>
                        )}
                    </div>
                </Col>

                {/* ── Assigned ──────────────────────────────────────────── */}
                <Col xs={6}>
                    <div className="small fw-semibold mb-1 text-muted">
                        Assigned ({assignedIds.size})
                    </div>
                    <Form.Control
                        size="sm"
                        placeholder="Search assigned…"
                        value={assignedQuery}
                        onChange={e => setAssignedQuery(e.target.value)}
                        className="mb-1"
                    />
                    <div id={assignedId} style={panelStyle}>
                        {assignedItems.length === 0 ? (
                            <div className="text-muted small text-center py-3">No keys assigned</div>
                        ) : (
                            <InfiniteScroll
                                dataLength={assignedItems.length}
                                next={() => fetchAssigned(assignedQuery, assignedOffset)}
                                hasMore={assignedHasMore}
                                loader={loader}
                                scrollableTarget={assignedId}
                            >
                                {assignedItems.map(t => renderRow(t, 'remove'))}
                            </InfiniteScroll>
                        )}
                    </div>
                </Col>
            </Row>

            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </>
    )
}

export default ScopeTokenAssigner
