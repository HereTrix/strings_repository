import { FC, useEffect, useState } from "react"
import StringToken from "../model/StringToken"
import Project from "../model/Project"
import { Button, Collapse, Container, Dropdown, ListGroup, Stack } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import AddTokenPage from "./AddTokenPage"
import SearchBar from "../UI/SearchBar"
import AddTokenTagPage from "./AddTokenTagPage"
import TokenTranslationsPage from "./TokenTranslationsPage"

type StringTokenProps = {
    project: Project
}

type StringTokenItemProps = {
    project_id: number
    token: StringToken
    onAddTag: () => void
    onDelete: () => void
}

const StringTokenListItem: FC<StringTokenItemProps> = ({ project_id, token, onAddTag, onDelete }) => {

    const [open, setOpen] = useState<boolean>(false)

    return (
        <ListGroup.Item
            className="d-flex justify-content-between align-items-start">
            <Container>
                <Container
                    onClick={() => setOpen(!open)}
                    className="d-flex justify-content-between align-items-start"
                >
                    <label>{token.token}</label>
                    <Stack
                        direction="horizontal"
                        gap={3}
                    >
                        <Button onClick={onAddTag}>Add tag</Button>
                        <Button onClick={onDelete} className="btn-danger">Delete</Button>
                    </Stack>
                </Container>
                <Collapse in={open}>
                    <div>
                        <TokenTranslationsPage project_id={project_id} token={token} open={open} />
                    </div>
                </Collapse>
            </Container>
        </ListGroup.Item >
    )
}

const StringTokensList: FC<StringTokenProps> = ({ project }) => {

    const [showDialog, setShowDialog] = useState(false)
    const [tokens, setTokens] = useState<StringToken[]>()
    const [tags, setTags] = useState<string[]>([])
    const [selectedTag, setSelectedTag] = useState<string>()
    const [query, setQuery] = useState<string>("")
    const [selectedToken, setSelectedToken] = useState<StringToken>()

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

        const result = await http<StringToken[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tokens`,
            params: params
        })

        if (result.value) {
            setTokens(result.value)
        }
    }

    const fetchTags = async () => {
        const result = await http<[string]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tags`
        })

        if (result.value) {
            setTags(result.value)
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

    const deleteToken = async (token: StringToken) => {
        const result = await http({
            method: APIMethod.delete,
            path: "/api/string_token",
            data: { "id": token.id }
        })

        if (result.error) {

        } else {
            fetch()
        }
    }

    useEffect(() => {
        fetch()
        fetchTags()
    }, [])

    return (
        <>
            <Stack direction="horizontal" gap={5}>
                <Button
                    onClick={() => setShowDialog(true)
                    } className="my-2" >
                    Add localization key
                </Button>
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
                {tokens && tokens.map((token) =>
                    <StringTokenListItem
                        key={token.id}
                        token={token}
                        project_id={project.id}
                        onAddTag={() => setSelectedToken(token)}
                        onDelete={() => deleteToken(token)} />
                )}
            </ListGroup>
            <AddTokenPage
                project_id={project.id}
                show={showDialog}
                onHide={() => setShowDialog(false)}
                onSuccess={fetch} />
            {selectedToken &&
                <AddTokenTagPage
                    token={selectedToken}
                    tags={tags}
                    onHide={() => setSelectedToken(undefined)}
                    onSuccess={() => { }}
                />
            }
        </>
    )
}

export default StringTokensList