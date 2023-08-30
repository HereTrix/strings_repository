import { FC, useState } from "react"
import { Button, Form, Modal, Row } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import { SubmitHandler, useForm } from "react-hook-form"

type AddTokenPageProps = {
    project_id: number
    show: boolean
    onHide: () => void
    onSuccess: () => void
}

type Inputs = {
    token: string
    comment: string | undefined
}

const AddTokenPage: FC<AddTokenPageProps> = ({ project_id, show, onHide, onSuccess }): JSX.Element => {

    const [error, setError] = useState([])

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {
        const result = await http({
            method: APIMethod.post,
            path: "/api/string_token",
            data: { "project": project_id, "token": data.token, "comment": data.comment }
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
                <Modal.Title>Add language</Modal.Title>
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