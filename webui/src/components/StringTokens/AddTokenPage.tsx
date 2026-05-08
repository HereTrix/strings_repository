import { FC, JSX, useState } from "react"
import { Button, Form, Modal } from "react-bootstrap"
import { APIMethod, BodyPayload, http } from "../../utils/network"
import { SubmitHandler, useForm } from "react-hook-form"
import { Typeahead } from "react-bootstrap-typeahead"

type AddTokenPageProps = {
    project_id: number
    show: boolean
    tags: string[]
    onHide: () => void
    onSuccess: () => void
}

type Inputs = {
    token: string
    comment?: string
}

const AddTokenPage: FC<AddTokenPageProps> = ({ project_id, show, tags, onHide, onSuccess }): JSX.Element => {

    const [error, setError] = useState([])
    const [selectedTags, setSelectedTags] = useState<string[] | null>(null)

    const {
        register,
        handleSubmit,
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {
        const payload: BodyPayload = {
            project: project_id,
            token: data.token,
            tags: selectedTags
        }
        if (data.comment) {
            payload.comment = data.comment
        }
        const result = await http({
            method: APIMethod.post,
            path: "/api/string_token",
            data: payload
        })

        if (result.error) {
            setError(error)
        } else {
            onSuccess()
            onHide()
        }
    }

    return (
        <Modal show={show} onHide={onHide}>
            <Modal.Header closeButton>
                <Modal.Title>Add localization key</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form onSubmit={handleSubmit(onSubmit)} className="container">
                    <Form.Group className="my-2">
                        <Form.Label>Localization key</Form.Label>
                        <Form.Control
                            required
                            type="text"
                            placeholder="Enter Localization key"
                            {...register("token")} />
                    </Form.Group>
                    <Form.Group>
                        <Form.Label>Tags</Form.Label>
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
                                    data.map((val) => typeof val === 'string' ? val : val.tag)
                                )
                            }}
                            selected={selectedTags ?? undefined}
                            className="my-2"
                        />
                    </Form.Group>
                    <Form.Group className="my-2">
                        <Form.Label>Comment</Form.Label>
                        <Form.Control
                            as="textarea"
                            placeholder="Enter comment"
                            {...register("comment")} />
                    </Form.Group>
                    {error && <Form.Label>{error}</Form.Label>}
                    <Button type="submit" className="my-2">Add</Button>
                </Form>
            </Modal.Body>
        </Modal>
    )
}

export default AddTokenPage