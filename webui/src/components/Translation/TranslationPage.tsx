import { FC, useCallback, useEffect, useState } from "react"
import { APIMethod, http } from "../../utils/network"
import Translation, { getStatusName, getStatusVariant, STATUS_OPTIONS, TranslationModel, UNTRANSLATED_FILTER } from "../../types/Translation"
import { Badge, Card, Container, ListGroup, Modal } from "react-bootstrap"
import PaginatedResponse from "../../types/PaginatedResponse"
import ErrorAlert from "../UI/ErrorAlert"
import InfiniteScroll from "react-infinite-scroll-component"
import TranslationListItem from "./TranslationListItem"
import Project from "../../types/Project"
import Scope from "../../types/Scope"
import FilterBar, { StatusOption } from "../UI/FilterBar"
import { usePagination, PAGE_LIMIT } from "../../hooks/usePagination"

type TranslationPageProps = {
    code: string
    project: Project
    scopeId?: number
    scope?: Scope
}

type Filters = {
    tags: string[]
    query: string
    status: string
}

const TranslationPage: FC<TranslationPageProps> = ({ code, project, scopeId, scope }) => {
    const defaultLanguageCode = project?.languages.find(l => l.is_default)?.code
    const [filters, setFilters] = useState<Filters>({ tags: [], query: '', status: 'all' })
    const [lightboxUrl, setLightboxUrl] = useState<string>()
    const { items: translations, offset, hasMore, setHasMore, total, handleResponse, setItems: setTranslations } = usePagination<TranslationModel>()
    const [tags, setTags] = useState<string[]>([])
    const [error, setError] = useState<string>()

    const fetchData = useCallback(async (pageOffset: number) => {
        const params: Record<string, any> = {}
        if (filters.tags?.length) params.tags = filters.tags
        if (filters.query) params.q = filters.query
        if (filters.status === UNTRANSLATED_FILTER) params.untranslated = 'true'
        else if (filters.status !== 'all') params.status = filters.status
        if (scopeId !== undefined) params.scope = String(scopeId)

        params.offset = `${pageOffset}`
        params.limit = `${PAGE_LIMIT}`

        const result = await http<PaginatedResponse<TranslationModel>>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/translations/${code}`,
            params,
        })

        if (result.value) handleResponse(result.value, pageOffset)
        else { setHasMore(false); setError(result.error) }
    }, [filters, project.id, code, scopeId, handleResponse, setHasMore])

    const fetchTags = useCallback(async () => {
        const result = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tags`
        })
        if (result.value) setTags(result.value)
        else setError(result.error)
    }, [project.id])

    useEffect(() => {
        fetchData(0)
    }, [fetchData])

    useEffect(() => {
        fetchTags()
    }, [fetchTags])

    const updateTranslationInList = (translation: TranslationModel, updates: Partial<TranslationModel>) => {
        setTranslations(prev => prev.map(t => t.token === translation.token ? { ...t, ...updates } : t))
    }

    const updateTranslationStatus = async (translation: TranslationModel, status: string) => {
        const previousStatus = translation.status
        updateTranslationInList(translation, { status })
        const result = await http<TranslationModel>({
            method: APIMethod.put,
            path: `/api/translation/status`,
            data: { project_id: project.id, code, token: translation.token, status }
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
            data: { project_id: project.id, code, token: translation.token, translation: translation.translation }
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
            {scope && (
                <Card className="mb-3 border-0 bg-body-tertiary">
                    <Card.Body className="py-2 px-3">
                        <div className="fw-semibold mb-1">{scope.name}</div>
                        {scope.description && (
                            <div className="text-muted small mb-2">{scope.description}</div>
                        )}
                        {scope.images.length > 0 && (
                            <div className="d-flex flex-wrap gap-2">
                                {scope.images.map(img => (
                                    <img
                                        key={img.id}
                                        src={img.url}
                                        alt=""
                                        style={{
                                            height: 64,
                                            maxWidth: 140,
                                            objectFit: 'cover',
                                            borderRadius: 6,
                                            cursor: 'pointer',
                                            border: '1px solid var(--bs-border-color)',
                                        }}
                                        onClick={() => setLightboxUrl(img.url)}
                                        title="Click to enlarge"
                                    />
                                ))}
                            </div>
                        )}
                    </Card.Body>
                </Card>
            )}

            {lightboxUrl && (
                <Modal show onHide={() => setLightboxUrl(undefined)} size="xl" centered>
                    <Modal.Header closeButton />
                    <Modal.Body className="p-0 text-center">
                        <img
                            src={lightboxUrl}
                            alt=""
                            style={{ maxWidth: '100%', maxHeight: '80vh', objectFit: 'contain' }}
                        />
                    </Modal.Body>
                </Modal>
            )}

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
                                        project_id={project.id.toString()}
                                        code={code}
                                        defaultLanguageCode={defaultLanguageCode}
                                        integrationEnabled={project.has_translation_integration}
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
