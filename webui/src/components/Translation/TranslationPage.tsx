import { FC, useCallback, useEffect, useState } from "react"
import { APIMethod, http } from "../Utils/network"
import Translation, { getStatusName, getStatusVariant, STATUS_OPTIONS, TranslationModel } from "../model/Translation"
import { Badge, Button, OverlayTrigger, Container, Dropdown, ListGroup, Stack, Card } from "react-bootstrap"
import PaginatedResponse from "../model/PaginatedResponse"
import SearchBar from "../UI/SearchBar"
import ErrorAlert from "../UI/ErrorAlert"
import InfiniteScroll from "react-infinite-scroll-component"
import { Typeahead } from "react-bootstrap-typeahead"
import HelpPopover from "../UI/HelpPopover"
import TranslationListItem from "./TranslationListItem"

type TranslationPageProps = {
    project_id: string
    code: string
}

type FilterStatus = 'all' | string

const TranslationPage: FC<TranslationPageProps> = ({ project_id, code }) => {
    const limit = 20
    const [hasMore, setHasMore] = useState<boolean>(true)
    const [offset, setOffset] = useState<number>(0)
    const [query, setQuery] = useState<string>("")
    const [statusFilter, setStatusFilter] = useState<FilterStatus>('all')

    const [translations, setTranslations] = useState<TranslationModel[]>([])
    const [total, setTotal] = useState<number>(0)
    const [tags, setTags] = useState<string[]>([])
    const [filteredTags, setFilteredTags] = useState<string[]>([])
    const [error, setError] = useState<string>()

    const fetchData = useCallback(async (
        tags: string[],
        term: string,
        newOffset: number,
        status: FilterStatus
    ) => {
        setOffset(newOffset)

        const params: Record<string, any> = {}
        if (tags?.length) params.tags = tags
        if (term) params.q = term
        else if (status !== 'all') params.status = status

        params.offset = `${newOffset}`
        params.limit = `${limit}`

        const result = await http<PaginatedResponse<TranslationModel>>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/translations/${code}`,
            params,
        })

        if (result.value) {
            setHasMore(result.value.results.length >= limit)
            setTotal(result.value.count)
            if (newOffset === 0) {
                setTranslations(result.value.results)
            } else {
                setTranslations(prev => [...prev, ...result.value!.results])
            }
        } else {
            setHasMore(false)
            setError(result.error)
        }
    }, [project_id, code])

    const fetchTags = useCallback(async () => {
        const result = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/tags`
        })
        if (result.value) setTags(result.value)
        else setError(result.error)
    }, [project_id])

    useEffect(() => {
        fetchData(filteredTags, query, 0, statusFilter)
        fetchTags()
    }, [])

    const onSearch = (newQuery: string) => {
        setQuery(newQuery)
        fetchData(filteredTags, newQuery, 0, statusFilter)
    }

    const filterTags = (newTags: string[]) => {
        setFilteredTags(newTags)
        fetchData(newTags, query, 0, statusFilter)
    }

    const updateTagSelection = (tag: string) => {
        const updated = filteredTags.includes(tag)
            ? filteredTags.filter(t => t !== tag)
            : [...filteredTags, tag]
        filterTags(updated)
    }

    const changeStatusFilter = (status: FilterStatus) => {
        setStatusFilter(status)
        fetchData(filteredTags, query, 0, status)
    }

    const updateTranslationInList = (translation: TranslationModel, updates: Partial<TranslationModel>) => {
        setTranslations(prev => prev.map(t => t.token === translation.token ? { ...t, ...updates } : t))
    }

    const updateTranslationStatus = async (translation: TranslationModel, status: string) => {
        const previousStatus = translation.status
        updateTranslationInList(translation, { status })
        const result = await http<TranslationModel>({
            method: APIMethod.put,
            path: `/api/translation/status`,
            data: { project_id, code, token: translation.token, status }
        })
        if (result.error) {
            setError(result.error)
            updateTranslationInList(translation, { status: previousStatus })
        }
    }

    const saveTranslation = async (translation: Translation) => {
        const result = await http({
            method: APIMethod.post,
            path: "/api/translation",
            data: { project_id, code, token: translation.token, translation: translation.translation }
        })
        if (result.error) setError(result.error)
    }

    const statusFilterOptions: { label: string, value: FilterStatus }[] = [
        { label: 'All', value: 'all' },
        ...STATUS_OPTIONS.map(s => ({ label: getStatusName(s), value: s }))
    ]

    return (
        <Container>
            <Stack direction="horizontal" gap={3}>
                <Stack direction="horizontal" gap={2}>
                    <span className="text-muted small">Status:</span>
                    <Dropdown>
                        <Dropdown.Toggle variant="outline-secondary">
                            {statusFilterOptions.find(o => o.value === statusFilter)?.label ?? 'All'}
                        </Dropdown.Toggle>
                        <Dropdown.Menu>
                            {statusFilterOptions.map(({ label, value }) => (
                                <Dropdown.Item
                                    key={value}
                                    active={statusFilter === value}
                                    onClick={() => changeStatusFilter(value)}
                                >
                                    {value !== 'all' && value !== 'untranslated' &&
                                        <Badge bg={getStatusVariant(value)} className="me-2">{label}</Badge>
                                    }
                                    {label}
                                </Dropdown.Item>
                            ))}
                        </Dropdown.Menu>
                    </Dropdown>
                </Stack>
                <Typeahead
                    id="tags-filter"
                    multiple
                    labelKey="tags"
                    options={tags}
                    placeholder="Filter by tags"
                    onChange={(data) => filterTags(data as string[])}
                    selected={filteredTags}
                    renderMenuItemChildren={(item) => <span>{item as string}</span>}
                />
                <SearchBar onSearch={onSearch} />
                <OverlayTrigger
                    trigger="click"
                    placement="left"
                    overlay={HelpPopover}
                >
                    <Button className="ms-auto" variant="outline-primary">
                        i
                    </Button>
                </OverlayTrigger>
            </Stack>

            {translations.length > 0 ? (
                <Card className="mt-3">
                    <Card.Header className="d-flex justify-content-between align-items-center">
                        <span className="fw-semibold">Translations</span>
                        <Badge bg="secondary">
                            {total} result{total !== 1 ? 's' : ''}
                        </Badge>
                    </Card.Header>
                    <Card.Body className="p-0">
                        <InfiniteScroll
                            dataLength={translations.length}
                            next={() => fetchData(filteredTags, query, offset + limit, statusFilter)}
                            hasMore={hasMore}
                            loader={<p>Loading...</p>}
                        >
                            <ListGroup className="mt-2">
                                {translations.map(translation => (
                                    <TranslationListItem
                                        key={translation.token}
                                        translation={translation}
                                        selectedTags={filteredTags}
                                        project_id={project_id}
                                        code={code}
                                        onSave={saveTranslation}
                                        onStatusChange={(status) => updateTranslationStatus(translation, status)}
                                        onTagClick={updateTagSelection}
                                        onError={msg => setError(msg)}
                                    />
                                ))}
                            </ListGroup>
                        </InfiniteScroll>
                    </Card.Body>
                </Card>
            ) : (
                <p className="text-muted mt-3">No translations found.</p>
            )}

            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </Container>
    )
}

export default TranslationPage