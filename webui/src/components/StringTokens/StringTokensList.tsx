import { FC, useCallback, useEffect, useState } from "react"
import StringToken, { getStatusVariant, STATUS_OPTIONS } from "../model/StringToken"
import PaginatedResponse from "../model/PaginatedResponse"
import Project from "../model/Project"
import { Badge, Button, Card, Dropdown, ListGroup, OverlayTrigger, Stack } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import AddTokenPage from "./AddTokenPage"
import SearchBar from "../UI/SearchBar"
import AddTokenTagPage from "./AddTokenTagPage"
import ErrorAlert from "../UI/ErrorAlert"
import InfiniteScroll from "react-infinite-scroll-component"
import ConfirmationAlert from "../UI/ConfirmationAlert"
import HelpPopover from "../UI/HelpPopover"
import { Typeahead } from "react-bootstrap-typeahead"
import StringTokenListItem from "./StringTokenListItem"

type StringTokenProps = {
    project: Project
}

type StatusFilter = 'all' | string

const StringTokensList: FC<StringTokenProps> = ({ project }) => {
    const limit = 20
    const [hasMore, setHasMore] = useState<boolean>(true)
    const [offset, setOffset] = useState<number>(0)
    const [showDialog, setShowDialog] = useState(false)
    const [tokens, setTokens] = useState<StringToken[]>([])
    const [tags, setTags] = useState<string[]>([])
    const [selectedTags, setSelectedTags] = useState<string[]>([])
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
    const [query, setQuery] = useState<string>("")
    const [selectedToken, setSelectedToken] = useState<StringToken>()
    const [error, setError] = useState<string>()
    const [deletionItem, setDeletionItem] = useState<StringToken>()
    const [total, setTotal] = useState<number>(0)

    const updateTokenInList = (id: string, changes: Partial<StringToken>) => {
        setTokens(prev => prev.map(t => t.id === id ? { ...t, ...changes } : t))
    }

    const fetchData = useCallback(async (
        tags: string[],
        term: string,
        newOffset: number,
        status: StatusFilter
    ) => {
        setOffset(newOffset)

        const params: Record<string, any> = {}
        if (tags?.length) params.tags = tags
        if (term) params.q = term
        if (status !== 'all') params.status = status

        params.offset = `${newOffset}`
        params.limit = `${limit}`

        const result = await http<PaginatedResponse<StringToken>>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tokens`,
            params,
        })

        if (result.value) {
            setHasMore(result.value.results.length >= limit)
            setTotal(result.value.count)
            if (newOffset === 0) {
                setTokens(result.value.results)
            } else {
                setTokens(prev => [...prev, ...result.value!.results])
            }
        } else {
            setHasMore(false)
            setError(result.error)
        }
    }, [project.id])

    const fetchTags = useCallback(async () => {
        const result = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tags`
        })
        if (result.value) setTags(result.value)
        else setError(result.error)
    }, [project.id])

    useEffect(() => {
        fetchData(selectedTags, query, 0, statusFilter)
        fetchTags()
    }, [])

    const onSearch = (newQuery: string) => {
        setQuery(newQuery)
        fetchData(selectedTags, newQuery, 0, statusFilter)
    }

    const selectTags = (newTags: string[]) => {
        setSelectedTags(newTags)
        fetchData(newTags, query, 0, statusFilter)
    }

    const updateTagSelection = (tag: string) => {
        const updated = selectedTags.includes(tag)
            ? selectedTags.filter(t => t !== tag)
            : [...selectedTags, tag]
        selectTags(updated)
    }

    const changeStatusFilter = (status: StatusFilter) => {
        setStatusFilter(status)
        fetchData(selectedTags, query, 0, status)
    }

    const deleteToken = async (token: StringToken) => {
        setDeletionItem(undefined)
        const result = await http({
            method: APIMethod.delete,
            path: "/api/string_token",
            data: { id: token.id }
        })
        if (result.error) setError(result.error)
        else fetchData(selectedTags, query, 0, statusFilter)
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

    return (
        <>
            <Stack direction="vertical" gap={2} className="my-3">
                <Stack direction="horizontal" gap={5}>
                    <Button onClick={() => setShowDialog(true)} className="my-2">
                        Add localization key
                    </Button>
                </Stack>
                <Stack direction="horizontal" gap={2}>
                    {/* Status filter */}
                    <Stack direction="horizontal" gap={2}>
                        <span className="text-muted small">Status:</span>
                        <Dropdown>
                            <Dropdown.Toggle variant="outline-secondary" size="sm" className="text-capitalize">
                                {statusFilter === 'all' ? 'All' : statusFilter}
                            </Dropdown.Toggle>
                            <Dropdown.Menu>
                                <Dropdown.Item active={false} onClick={() => changeStatusFilter('all')}>
                                    All
                                </Dropdown.Item>
                                <Dropdown.Divider />
                                {STATUS_OPTIONS.map(status => (
                                    <Dropdown.Item
                                        key={status}
                                        active={false}
                                        className="text-capitalize"
                                        onClick={() => changeStatusFilter(status)}
                                    >
                                        <Badge bg={getStatusVariant(status)} className="me-2">
                                            {status}
                                        </Badge>
                                        {status}
                                    </Dropdown.Item>
                                ))}
                            </Dropdown.Menu>
                        </Dropdown>
                    </Stack>
                    {/* Tags filter */}
                    {tags &&
                        <Typeahead
                            id="basic-typeahead-multiple"
                            multiple
                            options={tags}
                            placeholder="Tags filter"
                            onChange={(data) => selectTags(data as string[])}
                            selected={selectedTags}
                        />
                    }
                    {/* Search bar */}
                    <SearchBar onSearch={onSearch} />
                    {/* Info button */}
                    <OverlayTrigger trigger="click" placement="left" overlay={HelpPopover}>
                        <Button className="ms-auto" variant="outline-primary">i</Button>
                    </OverlayTrigger>
                </Stack>
            </Stack>

            {tokens &&
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
                            next={() => fetchData(selectedTags, query, offset + limit, statusFilter)}
                            hasMore={hasMore}
                            loader={<p>Loading...</p>}
                        >
                            <ListGroup>
                                {tokens.map(token =>
                                    <StringTokenListItem
                                        key={token.id}
                                        token={token}
                                        project_id={project.id}
                                        selectedTags={selectedTags}
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
            }

            {showDialog &&
                <AddTokenPage
                    project_id={project.id}
                    show={showDialog}
                    tags={tags}
                    onHide={() => setShowDialog(false)}
                    onSuccess={() => { fetchData(selectedTags, query, 0, statusFilter); setShowDialog(false) }}
                />
            }
            {selectedToken &&
                <AddTokenTagPage
                    token={selectedToken}
                    tags={tags}
                    onHide={() => setSelectedToken(undefined)}
                    onSuccess={() => {
                        fetchData(selectedTags, query, 0, statusFilter)
                        fetchTags()
                        setSelectedToken(undefined)
                    }}
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
        </>
    )
}

export default StringTokensList