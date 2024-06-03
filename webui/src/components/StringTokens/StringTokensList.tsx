import { FC, useEffect, useState } from "react"
import StringToken from "../model/StringToken"
import Project from "../model/Project"
import { Button, ButtonGroup, Collapse, Container, Dropdown, ListGroup, OverlayTrigger, Stack } from "react-bootstrap"
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
import { Typeahead } from "react-bootstrap-typeahead"

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
                        >Edit tags</Button>
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
    const [tokens, setTokens] = useState<StringToken[]>([])
    const [tags, setTags] = useState<string[]>([])
    const [selectedTags, setSelectedTags] = useState<string[]>([])
    const [untranslatedOnly, setUntranslatedOnly] = useState<boolean>(false)
    const [query, setQuery] = useState<string>("")
    const [selectedToken, setSelectedToken] = useState<StringToken>()
    const [error, setError] = useState<string>()
    const [deletionItem, setDeletionItem] = useState<StringToken>()

    const fetch = async () => {
        fetchData(selectedTags, query, offset, untranslatedOnly)
    }

    const fetchData = async (
        tags: string[],
        term: string,
        newOffset: number,
        untranslated: boolean
    ) => {
        setOffset(newOffset)
        if (newOffset === 0) {
            setHasMore(true)
        }
        var params = new Map<string, any>()
        if (tags.length > 0) {
            params.set('tags', tags)
        }

        if (term) {
            params.set('q', term)
        }

        if (untranslated) {
            params.set('new', true)
        }

        params.set('offset', `${newOffset}`)
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

            if (newOffset === 0) {
                setTokens(result.value)
            } else {
                setTokens(tokens.concat(result.value))
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
        } else {
            setError(result.error)
        }
    }

    const selectTags = async (tags: string[]) => {
        setSelectedTags(tags)
        fetchData(tags, query, 0, untranslatedOnly)
    }

    const udateTagSelection = async (tag: string) => {
        const idx = selectedTags.indexOf(tag)
        if (idx >= 0) {
            selectedTags.splice(idx, 1)
            selectTags(selectedTags)
        } else {
            var tags = selectedTags
            tags.push(tag)
            selectTags(tags)
        }
    }

    const onSearch = async (query: string) => {
        setQuery(query)
        fetchData(selectedTags, query, 0, untranslatedOnly)
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

    const toggleAll = () => {
        setUntranslatedOnly(false)
        fetchData(selectedTags, query, 0, false)
    }

    const toggleUntranslated = () => {
        setUntranslatedOnly(true)
        fetchData(selectedTags, query, 0, true)
    }

    useEffect(() => {
        fetch()
        fetchTags()
    }, [])

    return (
        <>
            <Stack direction="vertical" gap={2} className="my-3">
                <Stack direction="horizontal" gap={5}>
                    <Button
                        onClick={() => setShowDialog(true)
                        } className="my-2" >
                        Add localization key
                    </Button>
                    {tags && <>
                        <Typeahead
                            id="basic-typeahead-multiple"
                            multiple
                            labelKey="tags"
                            options={tags}
                            placeholder="Tags filter"
                            onChange={(data) => { selectTags(data as string[]) }}
                            selected={selectedTags}
                            renderMenuItemChildren={(item) => {
                                return (
                                    <Stack direction="horizontal" gap={3}>
                                        <label className="align-items-center display-linebreak">{item as string}</label>
                                    </Stack>
                                )
                            }}
                        />
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
                        New
                    </Button>
                </ButtonGroup>
            </Stack >
            {tokens &&
                <InfiniteScroll
                    dataLength={tokens.length}
                    next={() => {
                        const newOffset = offset + limit
                        fetchData(selectedTags, query, newOffset, untranslatedOnly)
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
                                onTagClick={(tag => udateTagSelection(tag))}
                            />
                        )}
                    </ListGroup>
                </InfiniteScroll>
            }
            {
                showDialog && <AddTokenPage
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
            {
                selectedToken &&
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
            {
                deletionItem && <ConfirmationAlert
                    message={`You are going to remove item ${deletionItem?.token}`}
                    onDismiss={() => setDeletionItem(undefined)}
                    onConfirm={() => deleteToken(deletionItem)}
                />
            }
        </>
    )
}

export default StringTokensList