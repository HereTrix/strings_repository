import { FC } from "react"
import { Container } from "react-bootstrap"

type TagsContainerProps = {
    tags: string[]
    selectedTags: string[]
    onTagClick: (tag: string) => void
}

const TagsContainer: FC<TagsContainerProps> = ({ tags, selectedTags, onTagClick }) => {

    return <Container className="ms-auto d-flex flex-wrap flex-row-reverse">
        {tags && tags.map((tag) =>
            <div
                className={`${selectedTags.includes(tag) ? "bg-primary" : "bg-secondary"} text-white px-2 border rounded d-inline-flex ms-1 text-nowrap col-auto`}
                onClick={(e) => {
                    e.stopPropagation()
                    onTagClick(tag)
                }}
                key={tag}
            >
                {tag}
            </div>
        )}
    </Container >
}

export default TagsContainer