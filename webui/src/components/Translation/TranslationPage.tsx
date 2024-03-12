import { ChangeEventHandler, FC, useEffect, useState } from "react"
import { APIMethod, http } from "../Utils/network"
import Translation, { TranslationModel } from "../model/Translation"
import { Button, Container, Dropdown, ListGroup, Row, Stack } from "react-bootstrap"
import ExportPage from "./ExportPage"
import SearchBar from "../UI/SearchBar"
import TagsContainer from "../UI/TagsContainer"
import ErrorAlert from "../UI/ErrorAlert"
import InfiniteScroll from "react-infinite-scroll-component"

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

const TranslationPage: FC<TranslationPageProps> = ({ project_id, code, untranslated }) => {

    const limit = 20
    const [hasMore, setHasMore] = useState<boolean>(true)
    const [offset, setOffset] = useState<number>(0)

    const [translations, setTranslations] = useState<TranslationModel[]>()

    const [selectedTag, setSelectedTag] = useState<string>()
    const [query, setQuery] = useState<string>("")
    const [tags, setTags] = useState<string[]>([])
    const [filteredTags, setFilteredTags] = useState<string[]>([])

    const [error, setError] = useState<string>()

    const fetch = async () => {
        fetchData(selectedTag, query, offset)
    }

    const fetchData = async (tag: string | undefined, term: string, offset: number) => {
        var params = new Map<string, string>()
        if (tag) {
            params.set('tags', tag)
        }

        if (term) {
            params.set('q', term)
        }

        params.set('offset', `${offset}`)
        params.set('limit', `${limit}`)
        params.set('untranslated', `${untranslated}`)

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
            if (offset === 0) {
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
            setFilteredTags(result.value)
        } else {
            setError(result.error)
        }
    }

    const selectTag = async (tag: string | undefined) => {
        setOffset(0)
        setSelectedTag(tag)
        fetchData(tag, query, 0)
    }

    const onSearch = async (query: string) => {
        setOffset(0)
        setQuery(query)
        fetchData(selectedTag, query, 0)
    }

    const onFilterTags = (query: string) => {
        const filtered = tags.filter((value) => value.includes(query))
        setFilteredTags(filtered)
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
            <Stack direction="horizontal" gap={5}>
                {filteredTags && <>
                    <Dropdown className="my-2">
                        <Dropdown.Toggle variant="success" id="dropdown-basic">
                            {selectedTag ? selectedTag : "Filter by tag"}
                        </Dropdown.Toggle>
                        <Dropdown.Menu>
                            <SearchBar onSearch={(query) => { }} onChange={onFilterTags} />
                            {selectedTag &&
                                <Dropdown.Item
                                    onClick={() => selectTag(undefined)}
                                    style={{ backgroundColor: "red", color: "white" }}
                                >
                                    Clear
                                </Dropdown.Item>
                            }
                            {filteredTags.map((tag) =>
                                <Dropdown.Item onClick={() => selectTag(tag)} key={tag}>{tag}</Dropdown.Item>
                            )}
                        </Dropdown.Menu>
                    </Dropdown>
                </>
                }
                <SearchBar onSearch={onSearch} />
            </Stack>
            {translations &&
                translations.length > 0 ?
                <InfiniteScroll
                    dataLength={translations.length}
                    next={() => {
                        const newOffset = offset + limit
                        setOffset(newOffset)
                        fetchData(selectedTag, query, newOffset)
                    }}
                    hasMore={hasMore}
                    loader={<p>Loading...</p>}
                >
                    <ListGroup>
                        {translations.map(
                            (translation) => <TranslationListItem
                                translation={translation}
                                onSave={saveTranslation}
                                onTagClick={tag => setSelectedTag(tag)}
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