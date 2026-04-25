import { FC } from "react"
import { Typeahead } from "react-bootstrap-typeahead"
import "../../styles/typeahead-dark.css"

type TagFilterProps = {
    id: string
    tags: string[]
    selected: string[]
    onChange: (tags: string[]) => void
    placeholder?: string
    size?: 'sm' | 'lg'
}

const TagFilter: FC<TagFilterProps> = ({
    id,
    tags,
    selected,
    onChange,
    placeholder = "Filter by tags",
    size,
}) => (
    <Typeahead
        id={id}
        multiple
        options={tags}
        selected={selected}
        onChange={t => onChange(t as string[])}
        placeholder={placeholder}
        size={size}
    />
)

export default TagFilter
