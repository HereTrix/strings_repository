import React, { useEffect, useState } from "react"
import { Button, Col, Container, Form, Row, Toast, ToastContainer } from "react-bootstrap";
import { useForm, SubmitHandler } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { APIMethod, http } from "./Utils/network";

type Inputs = {
    login: string
    password: string
}

type LoginResponse = {
    token: string
}

const LoginPage = () => {

    const navigate = useNavigate()

    const [validated, setValidated] = useState(false);
    const [error, setError] = useState<string | null>(null)

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {

        const result = await http<LoginResponse>({
            isAuth: true,
            method: APIMethod.post,
            path: "api/login",
            data: { "username": data.login, "password": data.password }
        })

        const error = result.error
        if (error) {
            setError(error)
            return
        }

        const token = result.value?.token
        if (token) {
            localStorage.setItem("auth", "Token " + token)
            navigate("/", { replace: true })
        }

    }

    return (
        <>
            <Container className="align-content-center" fluid>
                <Form validated={validated} onSubmit={handleSubmit(onSubmit)} className="container">
                    <Row className="mb-3">
                        <Form.Group>
                            <Form.Label>Login</Form.Label>
                            <Form.Control
                                required
                                type="text"
                                placeholder="Enter login"
                                {...register("login")} />
                        </Form.Group>
                    </Row>
                    <Row className="mb-3">
                        <Form.Group>
                            <Form.Label>Password</Form.Label>
                            <Form.Control
                                required
                                type="password"
                                placeholder="Enter password"
                                {...register("password")} />
                        </Form.Group>
                    </Row>
                    <Button type="submit" className="mb-2">Login</Button>
                </Form >
            </Container>
            <ToastContainer className="p-3" position="middle-center">
                <Toast show={error ? true : false} onClose={() => setError(null)} delay={3000} autohide>
                    <Toast.Header>
                        <strong className="me-auto">Error</strong>
                    </Toast.Header>
                    <Toast.Body>{error}</Toast.Body>
                </Toast>
            </ToastContainer>
        </>
    );
}

export default LoginPage;