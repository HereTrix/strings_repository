import { FC, useCallback, useEffect, useState } from "react"
import StringToken, { getStatusName, getStatusVariant, STATUS_OPTIONS } from "../../types/StringToken"
import PaginatedResponse from "../../types/PaginatedResponse"
import Project, { ProjectRole } from "../../types/Project"
import { Badge, Button, Card, Container, Dropdown, ListGroup } from "react-bootstrap"
import { APIMethod, http } from "../../utils/network"
import AddTokenPage from "./AddTokenPage"
import ErrorAlert from "../UI/ErrorAlert"
import InfiniteScroll from "react-infinite-scroll-component"
import ConfirmationAlert from "../UI/ConfirmationAlert"
import FilterBar, { StatusOption } from "../UI/FilterBar"
import AddTokenTagPage from "./AddTokenTagPage"
import StringTokenListItem from "./StringTokenListItem"
import { usePagination, PAGE_LIMIT } from "../../hooks/usePagination"
import ScopeManager from "./ScopeManager"
import Scope from "../../types/Scope"

type StringTokenProps = {
    project: Project
}

type Filters = {
    tags: string[]
    query: string
    status: string
    untranslated: boolean
    scope: number | undefined
}

const StringTokensList: FC<StringTokenProps> = ({ project }) => {
    const [filters, setFilters] = useState<Filters>({ tags: [], query: '', status: 'all', untranslated: false, scope: undefined })
    const { items: tokens, offset, hasMore, setHasMore, total, handleResponse, setItems: setTokens } = usePagination<StringToken>()
    const [showDialog, setShowDialog] = useState(false)
    const [showScopeManager, setShowScopeManager] = useState(false)
    const [tags, setTags] = useState<string[]>([])
    const [scopes, setScopes] = useState<Scope[]>([])
    const [selectedToken, setSelectedToken] = useState<StringToken>()
    const [error, setError] = useState<string>()
    const [deletionItem, setDeletionItem] = useState<StringToken>()

    const updateTokenInList = (id: string, changes: Partial<StringToken>) => {
        setTokens(prev => prev.map(t => t.id === id ? { ...t, ...changes } : t))
    }

    const fetchData = useCallback(async (pageOffset: number) => {
        const params: Record<string, any> = {}
        if (filters.tags?.length) params.tags = filters.tags
        if (filters.query) params.q = filters.query
        if (filters.untranslated) params.untranslated = 'true'
        else if (filters.status !== 'all') params.status = filters.status
        if (filters.scope !== undefined) params.scope = String(filters.scope)

        params.offset = `${pageOffset}`
        params.limit = `${PAGE_LIMIT}`

        const result = await http<PaginatedResponse<StringToken>>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tokens`,
            params,
        })

        if (result.value) handleResponse(result.value, pageOffset)
        else { setHasMore(false); setError(result.error) }
    }, [filters, project.id, handleResponse, setHasMore])

    const fetchTags = useCallback(async () => {
        const result = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tags`
        })
        if (result.value) setTags(result.value)
        else setError(result.error)
    }, [project.id])

    const fetchScopes = useCallback(async () => {
        const result = await http<Scope[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/scopes`,
        })
        if (result.value) setScopes(result.value)
    }, [project.id])

    useEffect(() => {
        fetchData(0)
    }, [fetchData])

    useEffect(() => {
        fetchTags()
    }, [fetchTags])

    useEffect(() => {
        fetchScopes()
    }, [fetchScopes])

    const deleteToken = async (token: StringToken) => {
        setDeletionItem(undefined)
        const result = await http({
            method: APIMethod.delete,
            path: "/api/string_token",
            data: { id: token.id }
        })
        if (result.error) setError(result.error)
        else fetchData(0)
    }

    const updateTokenStatus = async (token: StringToken, status: string) => {
        const previousStatus = token.status
        updateTokenInList(token.id, { status })
        const result = await http<StringToken>({
            method: APIMethod.put,
            path: `/api/string_token/${token.id}/status`,
            data: { status },
        })
        if (result.error) {
            setError(result.error)
            updateTokenInList(token.id, { status: previousStatus })
        }
    }

    const updateTagSelection = (tag: string) => {
        setFilters(f => {
            const updated = f.tags.includes(tag)
                ? f.tags.filter(t => t !== tag)
                : [...f.tags, tag]
            return { ...f, tags: updated }
        })
    }

    const statusOptions: StatusOption[] = [
        { label: 'All', value: 'all' },
        ...STATUS_OPTIONS.map(s => ({
            label: getStatusName(s),
            value: s,
            badge: { variant: getStatusVariant(s), text: getStatusName(s) }
        }))
    ]

    const activeScopeName = scopes.find(s => s.id === filters.scope)?.name

    return (
        <Container>
            <Button onClick={() => setShowDialog(true)} className="my-3">
                Add localization key
            </Button>
            <FilterBar
                typeaheadId="tokens-tags-filter"
                statusOptions={statusOptions}
                statusFilter={filters.status}
                onStatusChange={(status) => setFilters(f => ({ ...f, status }))}
                dividerBeforeIndex={1}
                statusDisabled={filters.untranslated}
                tags={tags}
                selectedTags={filters.tags}
                onTagsChange={(newTags) => setFilters(f => ({ ...f, tags: newTags }))}
                onSearch={(query) => setFilters(f => ({ ...f, query }))}
                extraControls={
                    <>
                        {(project.role === ProjectRole.owner || project.role === ProjectRole.admin) && (
                            <Button
                                size="sm"
                                variant="outline-secondary"
                                onClick={() => setShowScopeManager(true)}
                            >
                                Manage Scopes
                            </Button>
                        )}
                        <Dropdown>
                            <Dropdown.Toggle variant="outline-secondary" size="sm">
                                {activeScopeName ?? 'Scope'}
                            </Dropdown.Toggle>
                            <Dropdown.Menu>
                                <Dropdown.Item
                                    active={filters.scope === undefined}
                                    onClick={() => setFilters(f => ({ ...f, scope: undefined }))}
                                >
                                    All
                                </Dropdown.Item>
                                {scopes.map(scope => (
                                    <Dropdown.Item
                                        key={scope.id}
                                        active={filters.scope === scope.id}
                                        onClick={() => setFilters(f => ({ ...f, scope: scope.id }))}
                                    >
                                        {scope.name}
                                    </Dropdown.Item>
                                ))}
                            </Dropdown.Menu>
                        </Dropdown>
                        <Button
                            variant={filters.untranslated ? 'danger' : 'outline-danger'}
                            size="sm"
                            onClick={() => setFilters(f => ({ ...f, untranslated: !f.untranslated }))}
                        >
                            Untranslated
                        </Button>
                    </>
                }
            />

            <Card className="mt-3">
                <Card.Header className="d-flex justify-content-between align-items-center">
                    <span className="fw-semibold">Localization keys</span>
                    {tokens.length > 0 &&
                        <Badge bg="secondary">
                            {total} key{total !== 1 ? 's' : ''}
                        </Badge>
                    }
                </Card.Header>
                <Card.Body className="p-0">
                    <InfiniteScroll
                        dataLength={tokens.length}
                        next={() => fetchData(offset + PAGE_LIMIT)}
                        hasMore={hasMore}
                        loader={<div className="text-center p-3 text-muted small">Loading...</div>}
                    >
                        <ListGroup>
                            {tokens.map(token =>
                                <StringTokenListItem
                                    key={token.id}
                                    token={token}
                                    project_id={project.id}
                                    selectedTags={filters.tags}
                                    onAddTag={() => setSelectedToken(token)}
                                    onDelete={() => setDeletionItem(token)}
                                    onTagClick={updateTagSelection}
                                    onStatusChange={(status) => updateTokenStatus(token, status)}
                                />
                            )}
                        </ListGroup>
                    </InfiniteScroll>
                </Card.Body>
            </Card>

            {showDialog &&
                <AddTokenPage
                    project_id={project.id}
                    show={showDialog}
                    tags={tags}
                    onHide={() => setShowDialog(false)}
                    onSuccess={() => { fetchData(0); setShowDialog(false) }}
                />
            }
            {selectedToken &&
                <AddTokenTagPage
                    token={selectedToken}
                    tags={tags}
                    onHide={() => setSelectedToken(undefined)}
                    onSuccess={() => {
                        fetchData(0)
                        fetchTags()
                        setSelectedToken(undefined)
                    }}
                />
            }
            {showScopeManager &&
                <ScopeManager
                    project={project}
                    onHide={() => { setShowScopeManager(false); fetchScopes() }}
                />
            }
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
            {deletionItem &&
                <ConfirmationAlert
                    message={`You are going to remove item ${deletionItem.token}`}
                    onDismiss={() => setDeletionItem(undefined)}
                    onConfirm={() => deleteToken(deletionItem)}
                />
            }
        </Container>
    )
}

export default StringTokensList
