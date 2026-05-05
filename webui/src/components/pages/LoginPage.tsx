import { useState } from "react"
import { Alert, Button, Container, Form, Spinner, Toast, ToastContainer } from "react-bootstrap";
import { useForm, SubmitHandler } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { APIMethod, http } from "../../utils/network";
import { base64urlToBuffer, bufferToBase64url, serializeAssertionCredential } from "../../utils/webauthn";
import ErrorAlert from "../UI/ErrorAlert";
import Profile from "../../types/Profile";

type Inputs = {
    login: string
    password: string
}

type LoginResponse = {
    token: string
    '2fa_required'?: true
    user?: Profile
    expired?: string
}

const webAuthnSupported = typeof window !== 'undefined' && !!window.PublicKeyCredential

const LoginPage = () => {

    const navigate = useNavigate()

    const [validated, setValidated] = useState(false)
    const [error, setError] = useState<string>()
    const [passkeyLoading, setPasskeyLoading] = useState(false)
    const [passkeyError, setPasskeyError] = useState<string | null>(null)

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
            setError(error)
            return
        }

        const value = result.value
        if (!value) return

        if (value['2fa_required']) {
            localStorage.setItem("auth", "Token " + value.token)
            navigate("/2fa-login", { replace: true })
            return
        }

        if (value.token) {
            localStorage.setItem("auth", "Token " + value.token)
            navigate("/", { replace: true })
        }

    }

    const handlePasskeyLogin = async () => {
        setPasskeyLoading(true)
        setPasskeyError(null)

        const beginRes = await http<{ publicKey: any }>({
            isAuth: true,
            method: APIMethod.post,
            path: '/api/passkey/auth/begin',
            data: {},
        })

        if (beginRes.error || !beginRes.value) {
            setPasskeyError('Could not start passkey login.')
            setPasskeyLoading(false)
            return
        }

        let credential: Credential | null
        try {
            const keyString = beginRes.value.publicKey
            const opts = JSON.parse(keyString)
            const requestOptions: CredentialRequestOptions = {
                publicKey: {
                    ...opts,
                    challenge: base64urlToBuffer(opts.challenge),
                    allowCredentials: (opts.allowCredentials || []).map((c: any) => ({
                        ...c,
                        id: base64urlToBuffer(c.id),
                    })),
                },
            }

            credential = await navigator.credentials.get(requestOptions)
        } catch {
            setPasskeyError('Passkey sign-in was cancelled.')
            setPasskeyLoading(false)
            return
        }

        if (!credential) {
            setPasskeyError('Passkey sign-in was cancelled.')
            setPasskeyLoading(false)
            return
        }

        const credJson = serializeAssertionCredential(credential as PublicKeyCredential)

        const completeRes = await http<{ token: string }>({
            isAuth: true,
            method: APIMethod.post,
            path: '/api/passkey/auth/complete',
            data: { credential: credJson },
        })

        if (completeRes.error || !completeRes.value) {
            setPasskeyError(completeRes.error || 'Passkey sign-in failed.')
            setPasskeyLoading(false)
            return
        }

        localStorage.setItem('auth', 'Token ' + completeRes.value.token)
        navigate('/', { replace: true })
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
                        {webAuthnSupported && (
                            <>
                                <hr />
                                <Button
                                    variant="outline-secondary"
                                    className="w-100"
                                    onClick={handlePasskeyLogin}
                                    disabled={passkeyLoading}
                                >
                                    {passkeyLoading ? <Spinner animation="border" size="sm" /> : 'Sign in with passkey'}
                                </Button>
                                {passkeyError && <Alert variant="danger" className="mt-2">{passkeyError}</Alert>}
                            </>
                        )}
                    </Form.Group>
                </Form >
            </Container>
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </>
    );
}

export default LoginPage;