import { ChangeEventHandler, FC, useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { APIMethod, http } from "../Utils/network"
import Translation, { TranslationModel } from "../model/Translation"
import { Button, Container, Dropdown, ListGroup, Row, Stack } from "react-bootstrap"
import { history } from "../Utils/history"
import ExportPage from "./ExportPage"
import Project from "../model/Project"
import SearchBar from "../UI/SearchBar"
import TagsContainer from "../UI/TagsContainer"
import ErrorAlert from "../UI/ErrorAlert"

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

const TranslationPage = () => {

    const { project_id, code } = useParams()
    const [showExport, setShowExport] = useState(false)

    const [project, setProject] = useState<Project>()
    const [translations, setTranslations] = useState<TranslationModel[]>()

    const [selectedTag, setSelectedTag] = useState<string>()
    const [query, setQuery] = useState<string>("")
    const [tags, setTags] = useState<string[]>([])

    const [error, setError] = useState<string>()

    const fetchProject = async () => {
        const data = await http<Project>({
            method: APIMethod.get,
            path: `/api/project/${project_id}`
        })

        if (data.value) {
            setProject(data.value)
        } else {
            setError(data.error)
        }
    }

    const fetch = async () => {
        fetchData(selectedTag, query)
    }

    const fetchData = async (tag: string | undefined, term: string) => {
        var params = new Map<string, string>()
        if (tag) {
            params.set('tags', tag)
        }

        if (term) {
            params.set('q', term)
        }

        const result = await http<TranslationModel[]>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/translations/${code}`,
            params: params
        })

        if (result.error) {
            setError(result.error)
        } else {
            setTranslations(result.value)
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

    const selectTag = async (tag: string | undefined) => {
        setSelectedTag(tag)
        fetchData(tag, query)
    }

    const onSearch = async (query: string) => {
        setQuery(query)
        fetchData(selectedTag, query)
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

    const backToProject = () => {
        history.navigate(`/project/${project_id}`, { replace: true })
    }

    const onExport = () => {
        setShowExport(true)
    }

    useEffect(() => {
        fetchProject()
        fetch()
        fetchTags()
    }, [])

    return (
        <Container>
            <Container className="d-flex justify-content-between align-items-start">
                <Button onClick={backToProject}>Back to project</Button>
                {project && <Button onClick={onExport}>Export</Button>}
            </Container>
            <label>This is translation for {code}</label>
            <Stack direction="horizontal" gap={5}>
                {tags && <>
                    <Dropdown className="my-2">
                        <Dropdown.Toggle variant="success" id="dropdown-basic">
                            {selectedTag ? selectedTag : "Filter by tag"}
                        </Dropdown.Toggle>
                        <Dropdown.Menu>
                            {selectedTag &&
                                <Dropdown.Item
                                    onClick={() => selectTag(undefined)}
                                    style={{ backgroundColor: "red", color: "white" }}
                                >
                                    Clear
                                </Dropdown.Item>
                            }
                            {tags.map((tag) =>
                                <Dropdown.Item onClick={() => selectTag(tag)} key={tag}>{tag}</Dropdown.Item>
                            )}
                        </Dropdown.Menu>
                    </Dropdown>
                </>
                }
                <SearchBar onSearch={onSearch} />
            </Stack>
            <ListGroup>
                {translations && translations.map(
                    (translation) => <TranslationListItem
                        translation={translation}
                        onSave={saveTranslation}
                        onTagClick={tag => setSelectedTag(tag)}
                        key={translation.token}
                    />
                )}
            </ListGroup>
            {project &&
                <ExportPage
                    project={project}
                    code={code}
                    show={showExport}
                    onHide={() => setShowExport(false)} />
            }
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </Container>
    )
}

export default TranslationPage