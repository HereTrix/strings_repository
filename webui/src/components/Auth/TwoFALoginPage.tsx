import { useState } from "react"
import { Button, Container, Form } from "react-bootstrap"
import { SubmitHandler, useForm } from "react-hook-form"
import { useNavigate } from "react-router-dom"
import { APIMethod, http } from "../../utils/network"
import ErrorAlert from "../UI/ErrorAlert"
import { TwoFALoginResponse } from "../../types/TwoFA"

type Inputs = {
    code: string
}

const TwoFALoginPage = () => {
    const navigate = useNavigate()
    const [error, setError] = useState<string>()

    const { register, handleSubmit } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {
        const result = await http<TwoFALoginResponse>({
            method: APIMethod.post,
            path: "/api/2fa/login",
            data: { code: data.code },
        })

        if (result.error) {
            setError(result.error)
            return
        }

        navigate("/", { replace: true })
    }

    return (
        <>
            <Container fluid className="align-content-center">
                <Form onSubmit={handleSubmit(onSubmit)} className="container my-2">
                    <Form.Group className="border rounded m-4 p-5 shadow">
                        <h5>Two-Factor Authentication</h5>
                        <Form.Text className="text-muted d-block mb-3">
                            Enter the 6-digit code from your authenticator app,
                            or one of your backup codes.
                        </Form.Text>
                        <Form.Group className="my-2">
                            <Form.Label>Authentication Code</Form.Label>
                            <Form.Control
                                required
                                type="text"
                                placeholder="123456"
                                autoComplete="one-time-code"
                                {...register("code")}
                            />
                        </Form.Group>
                        <Button type="submit" className="my-2">
                            Verify
                        </Button>
                    </Form.Group>
                </Form>
            </Container>
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </>
    )
}

export default TwoFALoginPage
