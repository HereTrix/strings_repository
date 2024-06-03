import { ChangeEventHandler, FC, useEffect, useState } from "react"
import { APIMethod, http } from "../Utils/network"
import Translation, { TranslationModel } from "../model/Translation"
import { Button, ButtonGroup, Container, Dropdown, ListGroup, Row, Stack } from "react-bootstrap"
import ExportPage from "./ExportPage"
import SearchBar from "../UI/SearchBar"
import TagsContainer from "../UI/TagsContainer"
import ErrorAlert from "../UI/ErrorAlert"
import InfiniteScroll from "react-infinite-scroll-component"
import { Typeahead } from "react-bootstrap-typeahead"

type TranslationListItemProps = {
    translation: TranslationModel,
    onSave: (translation: Translation) => void
    onTagClick: (tag: string) => void
}

const TranslationListItem: FC<TranslationListItemProps> = ({ translation, onSave, onTagClick }) => {

    const [canSave, setCanSave] = useState<boolean>(false)
    const [text, setText] = useState<string | undefined>(translation.translation)

    const onTranslationChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
        setText(event.target.value)
        setCanSave(true)
    }

    const save = () => {
        setCanSave(false)
        const newTranslation: Translation = { token: translation.token, translation: text }
        onSave(newTranslation)
    }

    return (
        <ListGroup.Item >
            <Stack>
                <Stack direction="horizontal" gap={4}>
                    <label>{translation.token}</label>
                    {translation.tags &&
                        <TagsContainer
                            tags={translation.tags}
                            onTagClick={onTagClick}
                        />}
                </Stack>
                <Row>
                    <textarea defaultValue={translation.translation} onChange={onTranslationChange} />
                    {canSave && <Button onClick={save} className="my-1">Save</Button>}
                </Row>
            </Stack>
        </ListGroup.Item>
    )
}

type TranslationPageProps = {
    untranslated: boolean,
    project_id: string,
    code: string
}

const TranslationPage: FC<TranslationPageProps> = ({ project_id, code }) => {

    // Request modifiers
    const limit = 20
    const [hasMore, setHasMore] = useState<boolean>(true)
    const [offset, setOffset] = useState<number>(0)
    const [query, setQuery] = useState<string>("")
    const [untranslatedOnly, setUntranslatedOnly] = useState<boolean>(false)

    // Data
    const [translations, setTranslations] = useState<TranslationModel[]>()

    // Tags
    const [tags, setTags] = useState<string[]>([])
    const [filteredTags, setFilteredTags] = useState<string[]>([])

    const [error, setError] = useState<string>()

    const fetch = async () => {
        fetchData(filteredTags, query, offset, untranslatedOnly)
    }

    const fetchData = async (
        tags: string[],
        term: string,
        newOffset: number,
        untranslated: boolean
    ) => {
        setOffset(newOffset)
        var params = new Map<string, any>()
        if (tags) {
            params.set('tags', tags)
        }

        if (term) {
            params.set('q', term)
        }

        params.set('offset', `${newOffset}`)
        if (newOffset === 0) {
            setHasMore(true)
        }

        params.set('limit', `${limit}`)
        if (untranslated) {
            params.set('untranslated', true)
        }

        const result = await http<TranslationModel[]>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/translations/${code}`,
            params: params
        })

        if (result.value) {
            if (result.value.length < limit) {
                setHasMore(false)
            } else {
                setHasMore(true)
            }
            if (newOffset === 0) {
                setTranslations(result.value)
            } else {
                setTranslations(translations?.concat(result.value))
            }
        } else {
            setHasMore(false)
            setError(result.error)
        }
    }

    const fetchTags = async () => {
        const result = await http<[string]>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/tags`
        })

        if (result.value) {
            setTags(result.value)
        } else {
            setError(result.error)
        }
    }

    const onSearch = async (query: string) => {
        setQuery(query)
        fetchData(filteredTags, query, 0, untranslatedOnly)
    }

    const filterTags = (tags: string[]) => {
        setFilteredTags(tags)
        fetchData(tags, query, 0, untranslatedOnly)
    }

    const udateTagSelection = async (tag: string) => {
        const idx = filteredTags.indexOf(tag)

        if (idx >= 0) {
            filteredTags.splice(idx, 1)
            filterTags(filteredTags)
        } else {
            var tags = filteredTags
            tags.push(tag)
            filterTags(tags)
        }
    }

    const toggleAll = () => {
        setUntranslatedOnly(false)
        fetchData(filteredTags, query, 0, false)
    }

    const toggleUntranslated = () => {
        setUntranslatedOnly(true)
        fetchData(filteredTags, query, 0, true)
    }

    const saveTranslation = async (translation: Translation) => {
        const result = await http({
            method: APIMethod.post,
            path: "/api/translation",
            data: { "project_id": project_id, "code": code, "token": translation.token, "translation": translation.translation }
        })

        if (result.error) {
            setError(result.error)
        } else {

        }
    }

    useEffect(() => {
        fetch()
        fetchTags()
    }, [])

    return (
        <Container>
            <Stack direction="vertical" gap={2}>
                <Stack direction="horizontal" gap={5}>
                    {filteredTags &&
                        <Typeahead
                            id="basic-typeahead-multiple"
                            multiple
                            labelKey="tags"
                            options={tags}
                            placeholder="Tags filter"
                            onChange={(data) => { filterTags(data as string[]) }}
                            selected={filteredTags}
                            renderMenuItemChildren={(item) => {
                                return (
                                    <Stack direction="horizontal" gap={3}>
                                        <label className="align-items-center display-linebreak">{item as string}</label>
                                    </Stack>
                                )
                            }}
                        />
                    }
                    <SearchBar onSearch={onSearch} />
                </Stack>
                <ButtonGroup>
                    <Button
                        className={untranslatedOnly ? "btn-secondary" : "btn-primary"}
                        onClick={() => toggleAll()}
                    >
                        All
                    </Button>
                    <Button
                        className={untranslatedOnly ? "btn-primary" : "btn-secondary"}
                        onClick={() => toggleUntranslated()}
                    >
                        Untranslated
                    </Button>
                </ButtonGroup>
            </Stack>
            {translations &&
                translations.length > 0 ?
                <InfiniteScroll
                    dataLength={translations.length}
                    next={() => {
                        const newOffset = offset + limit
                        fetchData(filteredTags, query, newOffset, untranslatedOnly)
                    }}
                    hasMore={hasMore}
                    loader={<p>Loading...</p>}
                >
                    <ListGroup>
                        {translations.map(
                            (translation) => <TranslationListItem
                                translation={translation}
                                onSave={saveTranslation}
                                onTagClick={tag => udateTagSelection(tag)}
                                key={translation.token}
                            />
                        )}
                    </ListGroup>
                </InfiniteScroll>
                : <label>All keys translated</label>
            }
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </Container>
    )
}

export default TranslationPage