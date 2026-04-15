import { FC, useCallback, useEffect, useState } from "react"
import { APIMethod, http } from "../Utils/network"
import Translation, { getStatusName, getStatusVariant, STATUS_OPTIONS, TranslationModel, UNTRANSLATED_FILTER } from "../model/Translation"
import { Badge, Card, Container, ListGroup } from "react-bootstrap"
import PaginatedResponse from "../model/PaginatedResponse"
import ErrorAlert from "../UI/ErrorAlert"
import InfiniteScroll from "react-infinite-scroll-component"
import TranslationListItem from "./TranslationListItem"
import Project from "../model/Project"
import FilterBar, { StatusOption } from "../UI/FilterBar"
import { usePagination, PAGE_LIMIT } from "../../hooks/usePagination"

type TranslationPageProps = {
    project_id: string
    code: string
    project?: Project
}

type Filters = {
    tags: string[]
    query: string
    status: string
}

const TranslationPage: FC<TranslationPageProps> = ({ project_id, code, project }) => {
    const defaultLanguageCode = project?.languages.find(l => l.is_default)?.code
    const [filters, setFilters] = useState<Filters>({ tags: [], query: '', status: 'all' })
    const { items: translations, offset, hasMore, setHasMore, total, handleResponse, setItems: setTranslations } = usePagination<TranslationModel>()
    const [tags, setTags] = useState<string[]>([])
    const [error, setError] = useState<string>()
    const [integrationEnabled, setIntegrationEnabled] = useState(false)

    const fetchData = useCallback(async (pageOffset: number) => {
        const params: Record<string, any> = {}
        if (filters.tags?.length) params.tags = filters.tags
        if (filters.query) params.q = filters.query
        if (filters.status === UNTRANSLATED_FILTER) params.untranslated = 'true'
        else if (filters.status !== 'all') params.status = filters.status

        params.offset = `${pageOffset}`
        params.limit = `${PAGE_LIMIT}`

        const result = await http<PaginatedResponse<TranslationModel>>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/translations/${code}`,
            params,
        })

        if (result.value) handleResponse(result.value, pageOffset)
        else { setHasMore(false); setError(result.error) }
    }, [filters, project_id, code, handleResponse, setHasMore])

    const fetchTags = useCallback(async () => {
        const result = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/tags`
        })
        if (result.value) setTags(result.value)
        else setError(result.error)
    }, [project_id])

    const fetchIntegration = useCallback(async () => {
        const result = await http<{ enabled: boolean }>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/integration`,
        })
        if (result.value) setIntegrationEnabled(result.value.enabled)
    }, [project_id])

    useEffect(() => {
        fetchData(0)
    }, [fetchData])

    useEffect(() => {
        fetchTags()
    }, [fetchTags])

    useEffect(() => {
        fetchIntegration()
    }, [fetchIntegration])

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
        {
            label: getStatusName(UNTRANSLATED_FILTER),
            value: UNTRANSLATED_FILTER,
            badge: { variant: getStatusVariant(UNTRANSLATED_FILTER), text: getStatusName(UNTRANSLATED_FILTER) }
        },
        ...STATUS_OPTIONS.map(s => ({
            label: getStatusName(s),
            value: s,
            badge: { variant: getStatusVariant(s), text: getStatusName(s) }
        }))
    ]

    return (
        <Container>
            <FilterBar
                typeaheadId="translations-tags-filter"
                statusOptions={statusOptions}
                statusFilter={filters.status}
                onStatusChange={(status) => setFilters(f => ({ ...f, status }))}
                dividerBeforeIndex={2}
                showActiveItems
                tags={tags}
                selectedTags={filters.tags}
                onTagsChange={(newTags) => setFilters(f => ({ ...f, tags: newTags }))}
                onSearch={(query) => setFilters(f => ({ ...f, query }))}
            />

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
                            next={() => fetchData(offset + PAGE_LIMIT)}
                            hasMore={hasMore}
                            loader={<div className="text-center p-3 text-muted small">Loading...</div>}
                        >
                            <ListGroup className="mt-2">
                                {translations.map(translation => (
                                    <TranslationListItem
                                        key={translation.token}
                                        translation={translation}
                                        selectedTags={filters.tags}
                                        project_id={project_id}
                                        code={code}
                                        defaultLanguageCode={defaultLanguageCode}
                                        integrationEnabled={integrationEnabled}
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
