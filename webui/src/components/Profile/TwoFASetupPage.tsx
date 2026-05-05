import { FC, useEffect, useState } from "react"
import { Button, Form } from "react-bootstrap"
import { SubmitHandler, useForm } from "react-hook-form"
import { useNavigate } from "react-router-dom"
import { APIMethod, http } from "../../utils/network"
import { TwoFASetupResponse } from "../../types/TwoFA"
import ErrorAlert from "../UI/ErrorAlert"

type Props = {
    hasTwoFA: boolean
    onStatusChange: () => void
}

type SetupState =
    | { phase: 'idle' }
    | { phase: 'setup'; otpauth_uri: string; qr_code: string; backup_codes: string[] }
    | { phase: 'done' }

type VerifyInputs = { code: string }
type DisableInputs = { code: string }

const TwoFASetupPage: FC<Props> = ({ hasTwoFA, onStatusChange }) => {
    const [setupState, setSetupState] = useState<SetupState>({ phase: 'idle' })
    const [error, setError] = useState<string>()
    const navigate = useNavigate()

    useEffect(() => {
        if (setupState.phase === 'done') {
            const timer = setTimeout(() => {
                localStorage.removeItem("auth")
                navigate("/login", { replace: true })
            }, 3000)
            return () => clearTimeout(timer)
        }
    }, [setupState.phase])

    const verifyForm = useForm<VerifyInputs>()
    const disableForm = useForm<DisableInputs>()

    const handleEnable = async () => {
        setError(undefined)
        const result = await http<TwoFASetupResponse>({
            method: APIMethod.post,
            path: '/api/2fa/setup',
        })
        if (result.error) {
            setError(result.error)
            return
        }
        if (result.value) {
            setSetupState({
                phase: 'setup',
                otpauth_uri: result.value.otpauth_uri,
                qr_code: result.value.qr_code,
                backup_codes: result.value.backup_codes,
            })
        }
    }

    const onVerify: SubmitHandler<VerifyInputs> = async (data) => {
        setError(undefined)
        const result = await http({
            method: APIMethod.post,
            path: '/api/2fa/verify',
            data: { code: data.code },
        })
        if (result.error) {
            setError(result.error)
            return
        }
        setSetupState({ phase: 'done' })
        onStatusChange()
    }

    const onDisable: SubmitHandler<DisableInputs> = async (data) => {
        setError(undefined)
        const result = await http({
            method: APIMethod.delete,
            path: '/api/2fa',
            data: { code: data.code },
        })
        if (result.error) {
            setError(result.error)
            return
        }
        onStatusChange()
    }

    if (hasTwoFA) {
        return (
            <>
                <p>Two-factor authentication is <strong>enabled</strong> on your account.</p>
                <Form onSubmit={disableForm.handleSubmit(onDisable)}>
                    <Form.Group className="my-2">
                        <Form.Label>Authentication Code</Form.Label>
                        <Form.Control
                            required
                            type="text"
                            placeholder="123456 or backup code"
                            {...disableForm.register("code")}
                        />
                    </Form.Group>
                    <Button variant="danger" type="submit" className="my-2">
                        Disable 2FA
                    </Button>
                </Form>
                {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
            </>
        )
    }

    if (setupState.phase === 'idle') {
        return (
            <>
                <p>Two-factor authentication is not enabled.</p>
                <Button onClick={handleEnable}>Enable 2FA</Button>
                {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
            </>
        )
    }

    if (setupState.phase === 'setup') {
        return (
            <>
                <p>Scan this QR code with your authenticator app:</p>
                <img
                    src={`data:image/png;base64,${setupState.qr_code}`}
                    alt="QR Code"
                    style={{ maxWidth: 200 }}
                />
                <p className="mt-2 text-muted small">
                    Or enter manually: <code>{setupState.otpauth_uri}</code>
                </p>

                <p className="mt-3"><strong>Backup codes (save these now — they won't be shown again):</strong></p>
                <pre className="border p-2 bg-light">{setupState.backup_codes.join('\n')}</pre>
                <Button
                    variant="outline-secondary"
                    size="sm"
                    className="mb-3"
                    onClick={() => navigator.clipboard.writeText(setupState.backup_codes.join('\n'))}
                >
                    Copy backup codes
                </Button>

                <Form onSubmit={verifyForm.handleSubmit(onVerify)}>
                    <Form.Group className="my-2">
                        <Form.Label>Verify with your authenticator app</Form.Label>
                        <Form.Control
                            required
                            type="text"
                            placeholder="123456"
                            autoComplete="one-time-code"
                            {...verifyForm.register("code")}
                        />
                    </Form.Group>
                    <Button type="submit" className="my-2">Confirm 2FA</Button>
                </Form>
                {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
            </>
        )
    }

    return (
        <>
            <p><strong>2FA is now active.</strong> You will be logged out in a moment — sign in again to complete verification.</p>
        </>
    )
}

export default TwoFASetupPage
