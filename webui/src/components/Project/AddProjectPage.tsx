import { FC, useState } from "react"
import { Button, Container, Form, Modal, ModalBody, Row } from "react-bootstrap"
import { SubmitHandler, useForm } from "react-hook-form"
import { APIMethod, http } from "../Utils/network"

type Inputs = {
    projectName: string
    description: string
}

type AddProjectProps = {
    show: boolean
    onHide: () => void
    onSuccess: () => void
}

const AddProjectPage: FC<AddProjectProps> = ({ show, onHide, onSuccess }) => {

    const [error, setError] = useState([])

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {

        const result = await http({
            method: APIMethod.post,
            path: "api/project",
            data: { "name": data.projectName, "description": data.description }
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
                <Modal.Title>Add project</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form onSubmit={handleSubmit(onSubmit)} className="container">
                    <Row className="mb-3">
                        <Form.Label>Project name</Form.Label>
                        <Form.Control
                            required
                            type="text"
                            placeholder="Enter project name"
                            {...register("projectName")} />
                    </Row>
                    <Row className="mb-3">
                        <Form.Label>Project description</Form.Label>
                        <Form.Control
                            as="textarea"
                            placeholder="Enter project description"
                            {...register("description")} />
                    </Row>
                    {error && <Form.Label>{error}</Form.Label>}
                    <Button type="submit" className="mb-2">
                        Create
                    </Button>
                </Form>
            </Modal.Body>
        </Modal>
    )
}

export default AddProjectPage