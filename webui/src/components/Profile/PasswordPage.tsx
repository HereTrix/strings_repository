import { useState } from "react"
import { Button, Container, Form, Row } from "react-bootstrap"
import { SubmitHandler, useForm } from "react-hook-form"
import { APIMethod, http } from "../Utils/network"

type Inputs = {
    password: string
    newPassword: string
    confirmPassword: string
}

const PasswordPage = () => {
    const [error, setError] = useState<string>()

    const {
        register,
        handleSubmit,
        formState: { errors },
        reset
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {
        if (data.newPassword != data.confirmPassword) {
            setError("Confirmed password should be same as new password")
        }

        const result = await http({
            method: APIMethod.post,
            path: "/api/password",
            data: { "password": data.password, "new_password": data.newPassword }
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
                className="align-items-start">
                <Form.Group className="my-2">
                    <Form.Label>Password</Form.Label>
                    <Form.Control
                        required
                        type="password"
                        placeholder="Enter password"
                        {...register("password")} />
                </Form.Group>
                <Form.Group className="my-2">
                    <Form.Label>New password</Form.Label>
                    <Form.Control
                        required
                        type="password"
                        placeholder="Enter new password"
                        {...register("newPassword")} />
                </Form.Group>
                <Form.Group className="my-2">
                    <Form.Label>Confirm password</Form.Label>
                    <Form.Control
                        required
                        type="password"
                        placeholder="Enter new password again"
                        {...register("confirmPassword")} />
                </Form.Group>
                {error &&
                    <Form.Label className="error">{error}</Form.Label>
                }
                <Form.Group className="my-2">
                    <Button type="submit">
                        Update
                    </Button>
                </Form.Group>
            </Form>
        </Container>
    )
}

export default PasswordPage