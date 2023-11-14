import { FC, useState } from "react"

type SearchBarProps = {
    onSearch: (query: string) => void
    onChange?: (query: string) => void
}

const SearchBar: FC<SearchBarProps> = ({ onSearch, onChange }) => {
    const [query, setQuery] = useState<string>("")

    const onClear = () => {
        setQuery("")
        onSearch("")
    }

    return (
        <div className="me-2 rounded-pill d-flex align-items-start">
            <input
                type="search"
                placeholder="Search"
                value={query}
                onChange={(e) => {
                    e.preventDefault()
                    setQuery(e.target.value)
                    if (onChange) {
                        onChange(e.target.value)
                    }
                }}
                onKeyDown={e => {
                    if (e.key == "Enter") {
                        onSearch(query)
                    }
                }}
            />
            {query && <button onClick={onClear}>X</button>}
        </div>
    )
}

export default SearchBar