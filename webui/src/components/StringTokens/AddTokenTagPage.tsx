import { FC, useState } from "react"
import { Button, Modal } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import { Typeahead } from "react-bootstrap-typeahead"
import StringToken from "../model/StringToken"
import ErrorAlert from "../UI/ErrorAlert"

type AddTokenTagPageProps = {
    token: StringToken
    tags: string[]
    onHide: () => void
    onSuccess: () => void
}

const AddTokenTagPage: FC<AddTokenTagPageProps> = ({ token, tags, onHide, onSuccess }) => {

    const [selectedTags, setSelectedTags] = useState<string[]>(token.tags ? token.tags : [])

    const [error, setError] = useState<string>()

    const onSubmit = async () => {

        if (!selectedTags) {
            return
        }

        const result = await http({
            method: APIMethod.post,
            path: `/api/string_token/${token.id}/tags`,
            data: { "tags": selectedTags }
        })

        if (result.error) {
            setError(result.error)
        } else {
            onSuccess()
        }
    }

    return (
        <Modal show={true} onHide={onHide}>
            <Modal.Header closeButton>
                <Modal.Title>Add Tag</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Typeahead
                    allowNew
                    newSelectionPrefix="Create tag: "
                    id="basic-typeahead-multiple"
                    multiple
                    labelKey={"tag"}
                    options={tags}
                    placeholder="Select tags..."
                    onChange={(data) => {
                        setSelectedTags(
                            data.map((val: any) => typeof val === 'string' ? val : val.tag)
                        )
                    }}
                    selected={selectedTags}
                    className="my-2"
                />
                <Button onClick={onSubmit} className="my-2">Add</Button>
            </Modal.Body>
            {error && <ErrorAlert
                error={error}
                onClose={() => setError(undefined)}
            />}
        </Modal>
    )
}

export default AddTokenTagPage