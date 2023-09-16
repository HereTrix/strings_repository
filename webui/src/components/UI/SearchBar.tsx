import { FC, useState } from "react"

type SearchBarProps = {
    onSearch: (query: string) => void
}

const SearchBar: FC<SearchBarProps> = ({ onSearch }) => {
    const [query, setQuery] = useState<string>("")

    const onClear = () => {
        setQuery("")
        onSearch("")
    }

    return (
        <div className="me-2 rounded-pill">
            <input
                type="search"
                placeholder="Search"
                value={query}
                onChange={(e) => {
                    e.preventDefault()
                    setQuery(e.target.value)
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