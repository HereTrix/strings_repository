import { FC, useEffect, useState } from "react"
import StringToken from "../model/StringToken"
import Project from "../model/Project"
import { Button, Collapse, Container, Dropdown, ListGroup, OverlayTrigger, Stack } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import AddTokenPage from "./AddTokenPage"
import SearchBar from "../UI/SearchBar"
import AddTokenTagPage from "./AddTokenTagPage"
import TokenTranslationsPage from "./TokenTranslationsPage"
import ErrorAlert from "../UI/ErrorAlert"
import TagsContainer from "../UI/TagsContainer"
import InfiniteScroll from "react-infinite-scroll-component"
import ConfirmationAlert from "../UI/ConfirmationAlert"
import HelpPopover from "../UI/HelpPopover"

type StringTokenProps = {
    project: Project
}

type StringTokenItemProps = {
    project_id: number
    token: StringToken
    onAddTag: () => void
    onDelete: () => void
    onTagClick: (tag: string) => void
}

const StringTokenListItem: FC<StringTokenItemProps> = ({ project_id, token, onAddTag, onDelete, onTagClick }) => {

    const [open, setOpen] = useState<boolean>(false)

    return (
        <ListGroup.Item
            className="d-flex justify-content-between align-items-start">
            <Container>
                <Stack direction="horizontal" gap={4}
                    onClick={() => setOpen(!open)}
                >
                    <label>{token.token}</label>
                    {token.tags &&
                        <TagsContainer
                            tags={token.tags}
                            onTagClick={onTagClick}
                        />}
                    <Stack
                        direction="horizontal"
                        gap={3}
                    >
                        <Button
                            onClick={(e) => {
                                e.stopPropagation()
                                onAddTag()
                            }}
                            className="text-nowrap"
                        >Add tag</Button>
                        <Button onClick={(e) => {
                            e.stopPropagation()
                            onDelete()
                        }} className="btn-danger">Delete</Button>
                    </Stack>
                </Stack>
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

    const limit = 20
    const [hasMore, setHasMore] = useState<boolean>(true)
    const [offset, setOffset] = useState<number>(0)

    const [showDialog, setShowDialog] = useState(false)
    const [tokens, setTokens] = useState<StringToken[]>()
    const [tags, setTags] = useState<string[]>([])
    const [filteredTags, setFilteredTags] = useState<string[]>([])
    const [selectedTag, setSelectedTag] = useState<string>()
    const [query, setQuery] = useState<string>("")
    const [selectedToken, setSelectedToken] = useState<StringToken>()
    const [error, setError] = useState<string>()
    const [deletionItem, setDeletionItem] = useState<StringToken>()

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

        const result = await http<StringToken[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tokens`,
            params: params
        })

        if (result.value) {
            if (result.value.length < limit) {
                setHasMore(false)
            } else {
                setHasMore(true)
            }
            if (offset === 0) {
                setTokens(result.value)
            } else {
                console.log('append')
                setTokens(tokens?.concat(result.value))
            }
        } else {
            setHasMore(false)
            setError(result.error)
        }
    }

    const fetchTags = async () => {
        const result = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tags`
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

    const deleteToken = async (token: StringToken) => {
        setDeletionItem(undefined)
        const result = await http({
            method: APIMethod.delete,
            path: "/api/string_token",
            data: { "id": token.id }
        })

        if (result.error) {
            setError(result.error)
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
                            <SearchBar onSearch={(query) => { }} onChange={onFilterTags} />
                            {filteredTags.map((tag) =>
                                <Dropdown.Item onClick={() => selectTag(tag)} key={tag}>{tag}</Dropdown.Item>
                            )}
                        </Dropdown.Menu>
                    </Dropdown>
                </>
                }
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
            {tokens &&
                <InfiniteScroll
                    dataLength={tokens.length}
                    next={() => {
                        const newOffset = offset + limit
                        setOffset(newOffset)
                        fetchData(selectedTag, query, newOffset)
                    }}
                    hasMore={hasMore}
                    loader={<p>Loading...</p>}
                >
                    <ListGroup>
                        {tokens.map((token) =>
                            <StringTokenListItem
                                key={token.id}
                                token={token}
                                project_id={project.id}
                                onAddTag={() => setSelectedToken(token)}
                                onDelete={() => setDeletionItem(token)}
                                onTagClick={(tag => selectTag(tag))}
                            />
                        )}
                    </ListGroup>
                </InfiniteScroll>
            }
            {showDialog && <AddTokenPage
                project_id={project.id}
                show={showDialog}
                tags={tags}
                onHide={() => setShowDialog(false)}
                onSuccess={() => {
                    fetch()
                    setShowDialog(false)
                }
                } />
            }
            {selectedToken &&
                <AddTokenTagPage
                    token={selectedToken}
                    tags={tags}
                    onHide={() => setSelectedToken(undefined)}
                    onSuccess={() => {
                        fetch()
                        fetchTags()
                        setSelectedToken(undefined)
                    }}
                />
            }
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
            {deletionItem && <ConfirmationAlert
                message={`You are going to remove item ${deletionItem?.token}`}
                onDismiss={() => setDeletionItem(undefined)}
                onConfirm={() => deleteToken(deletionItem)}
            />}
        </>
    )
}

export default StringTokensList