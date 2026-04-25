import { FC, Fragment, ReactNode } from "react"
import { Badge, Button, Dropdown, OverlayTrigger, Stack } from "react-bootstrap"
import SearchBar from "./SearchBar"
import HelpPopover from "./HelpPopover"
import TagFilter from "./TagFilter"

export type StatusOption = {
    label: string
    value: string
    badge?: { variant: string; text: string }
}

type FilterBarProps = {
    statusOptions: StatusOption[]
    statusFilter: string
    onStatusChange: (value: string) => void
    /** Insert a divider before the item at this index (0-based) */
    dividerBeforeIndex?: number
    statusDisabled?: boolean
    showActiveItems?: boolean
    tags: string[]
    selectedTags: string[]
    onTagsChange: (tags: string[]) => void
    onSearch: (query: string) => void
    /** Rendered between the status dropdown and tags filter (e.g. an Untranslated button) */
    extraControls?: ReactNode
    typeaheadId: string
}

const FilterBar: FC<FilterBarProps> = ({
    statusOptions,
    statusFilter,
    onStatusChange,
    dividerBeforeIndex,
    statusDisabled,
    showActiveItems,
    tags,
    selectedTags,
    onTagsChange,
    onSearch,
    extraControls,
    typeaheadId,
}) => {
    const currentLabel = statusOptions.find(o => o.value === statusFilter)?.label ?? 'All'

    return (
        <Stack direction="horizontal" gap={2}>
            <Stack direction="horizontal" gap={2}>
                <span className="text-muted small">Status:</span>
                <Dropdown>
                    <Dropdown.Toggle variant="outline-secondary" size="sm" disabled={statusDisabled}>
                        {currentLabel}
                    </Dropdown.Toggle>
                    <Dropdown.Menu>
                        {statusOptions.map(({ label, value, badge }, i) => (
                            <Fragment key={value}>
                                {dividerBeforeIndex !== undefined && i === dividerBeforeIndex && (
                                    <Dropdown.Divider />
                                )}
                                <Dropdown.Item
                                    active={showActiveItems ? statusFilter === value : false}
                                    onClick={() => onStatusChange(value)}
                                >
                                    {badge && <Badge bg={badge.variant} className="me-2">{badge.text}</Badge>}
                                    {label}
                                </Dropdown.Item>
                            </Fragment>
                        ))}
                    </Dropdown.Menu>
                </Dropdown>
            </Stack>
            {extraControls}
            <TagFilter
                id={typeaheadId}
                tags={tags}
                selected={selectedTags}
                onChange={onTagsChange}
            />
            <SearchBar onSearch={onSearch} />
            <OverlayTrigger trigger="click" placement="left" overlay={HelpPopover}>
                <Button className="ms-auto" variant="outline-primary">i</Button>
            </OverlayTrigger>
        </Stack>
    )
}

export default FilterBar
