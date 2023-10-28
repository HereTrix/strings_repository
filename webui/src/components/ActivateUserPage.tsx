import { useState } from "react"
import { Button, Container, Form, Toast, ToastContainer } from "react-bootstrap"
import { SubmitHandler, useForm } from "react-hook-form"
import { useNavigate } from "react-router-dom";
import { APIMethod, http } from "./Utils/network";

type Inputs = {
    login: string
    activationCode: string
    password: string
    confirmPassword: string
}

const ActivateUserPage = () => {

    const navigate = useNavigate()
    const [validated, setValidated] = useState(false);
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<boolean>(false)

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {
        if (data.password.length < 8) {
            setError("Password is too weak")
            return
        }

        if (data.password != data.confirmPassword) {
            setError("Passwords should match")
            return
        }

        const result = await http({
            method: APIMethod.post,
            path: "/api/signup",
            data: { "code": data.activationCode, "login": data.login, "password": data.password }
        })

        if (result.error) {
            setError(result.error)
        } else {
            setSuccess(true)
        }
    }

    const onBackToLogin = () => {
        navigate("/login", { replace: true })
    }

    return (
        <>
            <Container className="align-content-center" fluid>
                <Container className="align-content-right my-2 flex-row-reverse d-flex" fluid>
                    <Button onClick={onBackToLogin}>Back to login</Button>
                </Container>
                <Form validated={validated} onSubmit={handleSubmit(onSubmit)} className="container my-2">
                    <Form.Group className="border rounded m-4 p-5 shadow">
                        <Form.Group className="my-2">
                            <Form.Label>Activation code</Form.Label>
                            <Form.Control
                                required
                                type="text"
                                placeholder="Enter activation code"
                                {...register("activationCode")}
                            />
                        </Form.Group>
                        <Form.Group className="my-2">
                            <Form.Label>Login</Form.Label>
                            <Form.Control
                                required
                                type="text"
                                placeholder="Enter login"
                                {...register("login")}
                            />
                        </Form.Group>
                        <Form.Group className="my-2">
                            <Form.Label>Password</Form.Label>
                            <Form.Control
                                required
                                type="password"
                                placeholder="Enter password"
                                {...register("password")}
                            />
                        </Form.Group>
                        <Form.Group className="my-2">
                            <Form.Label>Confirm password</Form.Label>
                            <Form.Control
                                required
                                type="password"
                                placeholder="Confirm password"
                                {...register("confirmPassword")}
                            />
                        </Form.Group>
                        <Form.Group className="my-2">
                            <Button type="submit">Activate</Button>
                        </Form.Group>
                    </Form.Group>
                </Form>
            </Container>
            <ToastContainer className="p-3" position="middle-center">
                <Toast show={error ? true : false} onClose={() => setError(null)} delay={5000} autohide>
                    <Toast.Header>
                        <strong className="me-auto error">Error</strong>
                    </Toast.Header>
                    <Toast.Body>{error}</Toast.Body>
                </Toast>
                <Toast show={success} onClose={() => setSuccess(false)}>
                    <Toast.Header>
                        <strong className="me-auto text-success">Acccount activated.</strong>
                    </Toast.Header>
                    <Toast.Body>
                        <Container>
                            <label className="my-2">Please go to login page</label>
                            <Button onClick={onBackToLogin} className="my-2">Go To Login</Button>
                        </Container>
                    </Toast.Body>
                </Toast>
            </ToastContainer>
        </>
    )
}

export default ActivateUserPage