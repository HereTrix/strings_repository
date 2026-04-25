import { Badge, Button, Collapse, Container, Dropdown, ListGroup, Stack } from "react-bootstrap"
import { getStatusVariant, STATUS_OPTIONS } from "../../types/StringToken"
import TagsContainer from "../UI/TagsContainer"
import { FC, useState } from "react"
import StringToken from "../../types/StringToken"
import TokenTranslationsView from "./TokenTranslationsView"

type StringTokenItemProps = {
    project_id: number
    token: StringToken
    selectedTags: string[]
    onAddTag: () => void
    onDelete: () => void
    onTagClick: (tag: string) => void
    onStatusChange: (status: string) => void
}

const StringTokenListItem: FC<StringTokenItemProps> = ({ project_id, token, selectedTags, onAddTag, onDelete, onTagClick, onStatusChange }) => {
    const [open, setOpen] = useState<boolean>(false)

    return (
        <ListGroup.Item className="d-flex justify-content-between align-items-start">
            <Container>
                <Stack direction="horizontal" gap={4} onClick={() => setOpen(!open)}>
                    <span>{token.token}</span>
                    {token.tags &&
                        <TagsContainer
                            tags={token.tags}
                            selectedTags={selectedTags}
                            onTagClick={onTagClick}
                        />}
                    <Stack direction="horizontal" gap={3}>
                        <Dropdown onClick={(e) => e.stopPropagation()}>
                            <Dropdown.Toggle
                                variant={getStatusVariant(token.status)}
                                size="sm"
                                className="text-capitalize"
                            >
                                {token.status}
                            </Dropdown.Toggle>
                            <Dropdown.Menu>
                                {STATUS_OPTIONS.map(status => (
                                    <Dropdown.Item
                                        key={status}
                                        active={false}
                                        className="text-capitalize"
                                        onClick={() => onStatusChange(status)}
                                    >
                                        <Badge bg={getStatusVariant(status)} className="me-2">
                                            {status}
                                        </Badge>
                                        {status}
                                    </Dropdown.Item>
                                ))}
                            </Dropdown.Menu>
                        </Dropdown>
                        <Button
                            onClick={(e) => { e.stopPropagation(); onAddTag() }}
                            className="text-nowrap"
                        >Edit tags</Button>
                        <Button
                            onClick={(e) => { e.stopPropagation(); onDelete() }}
                            className="btn-danger"
                        >Delete</Button>
                    </Stack>
                </Stack>
                <Collapse in={open}>
                    <div>
                        <TokenTranslationsView project_id={project_id} token={token} open={open} />
                    </div>
                </Collapse>
            </Container>
        </ListGroup.Item>
    )
}

export default StringTokenListItem