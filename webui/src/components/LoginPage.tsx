import { useState } from "react"
import { Button, Container, Form, Toast, ToastContainer } from "react-bootstrap";
import { useForm, SubmitHandler } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { APIMethod, http } from "./Utils/network";
import ErrorAlert from "./UI/ErrorAlert";

type Inputs = {
    login: string
    password: string
}

type LoginResponse = {
    token: string
}

const LoginPage = () => {

    const navigate = useNavigate()

    const [validated, setValidated] = useState(false)
    const [error, setError] = useState<string>()

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {

        const result = await http<LoginResponse>({
            isAuth: true,
            method: APIMethod.post,
            path: "/api/login",
            data: { "username": data.login, "password": data.password }
        })

        const error = result.error
        if (error) {
            console.log(error)
            setError(error)
            return
        }

        const token = result.value?.token
        if (token) {
            localStorage.setItem("auth", "Token " + token)
            navigate("/", { replace: true })
        }

    }

    const onUserActivate = () => {
        navigate("/activate", { replace: true })
    }

    return (
        <>
            <Container className="align-content-center" fluid>
                <Form validated={validated} onSubmit={handleSubmit(onSubmit)} className="container my-2">
                    <Form.Group className="border rounded m-4 p-5 shadow">
                        <Form.Group className="my-2">
                            <Form.Label>Login</Form.Label>
                            <Form.Control
                                required
                                type="text"
                                placeholder="Enter login"
                                {...register("login")} />
                        </Form.Group>
                        <Form.Group className="my-2">
                            <Form.Label>Password</Form.Label>
                            <Form.Control
                                required
                                type="password"
                                placeholder="Enter password"
                                {...register("password")} />
                        </Form.Group>
                        <Form.Group className="my-2">
                            <Button type="submit" className="my-2">Login</Button>
                        </Form.Group>
                        <Form.Group className="my-2">
                            <Button onClick={onUserActivate} className="btn-light shadow-sm my-2">Activate user</Button>
                        </Form.Group>
                    </Form.Group>
                </Form >
            </Container>
            <ErrorAlert error={error} onClose={() => setError(undefined)} />
        </>
    );
}

export default LoginPage;