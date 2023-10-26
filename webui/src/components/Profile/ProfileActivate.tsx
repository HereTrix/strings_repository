import { useState } from "react"
import { Button, Container, Form, FormGroup } from "react-bootstrap"
import { SubmitHandler, useForm } from "react-hook-form"
import { APIMethod, http } from "../Utils/network"

type Inputs = {
    code: string
}

const ProfileActivatePage = () => {

    const [error, setError] = useState<string>()

    const {
        register,
        handleSubmit,
        formState: { errors },
        reset
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {
        const result = await http({
            method: APIMethod.post,
            path: "/api/activate",
            data: { "code": data.code }
        })

        if (result.error) {
            setError(result.error)
        } else {
            reset()
        }
    }

    return (
        <Container>
            <Form
                onSubmit={handleSubmit(onSubmit)}
                className="align-items-start"
            >
                <Form.Group className="my-2">
                    <Form.Label>Invitation code</Form.Label>
                    <Form.Control
                        required
                        type="text"
                        placeholder="Invitation code"
                        {...register("code")} />
                </Form.Group>
                <Form.Group className="my-2">
                    <Button
                        type="submit">
                        Save
                    </Button>
                </Form.Group>
                {error &&
                    <Form.Label className="error">{error}</Form.Label>
                }
            </Form>
        </Container>
    )
}

export default ProfileActivatePage