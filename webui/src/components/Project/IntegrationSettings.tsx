import { FC, useEffect, useState } from "react"
import { Alert, Badge, Button, Form, Spinner, Stack } from "react-bootstrap"
import Project, { ProjectRole } from "../model/Project"
import { APIMethod, http } from "../Utils/network"
import ErrorAlert from "../UI/ErrorAlert"

type Provider = {
    value: string
    label: string
}

type Integration = {
    enabled: boolean
    provider?: string
    provider_label?: string
    providers: Provider[]
}

type IntegrationSettingsProps = {
    project: Project
}

const IntegrationSettings: FC<IntegrationSettingsProps> = ({ project }) => {
    const isAdmin = project.role === ProjectRole.owner || project.role === ProjectRole.admin

    const [integration, setIntegration] = useState<Integration>()
    const [provider, setProvider] = useState('')
    const [apiKey, setApiKey] = useState('')
    const [error, setError] = useState<string>()
    const [success, setSuccess] = useState(false)
    const [verifying, setVerifying] = useState(false)
    const [verifyResult, setVerifyResult] = useState<{ ok: boolean; message?: string }>()

    const load = async () => {
        const result = await http<Integration>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/integration`,
        })
        if (result.value) {
            setIntegration(result.value)
            if (result.value.provider) {
                setProvider(result.value.provider)
            } else if (result.value.providers.length > 0) {
                setProvider(result.value.providers[0].value)
            }
        }
    }

    useEffect(() => {
        load()
    }, [])

    const save = async () => {
        setSuccess(false)
        setError(undefined)
        const result = await http({
            method: APIMethod.post,
            path: `/api/project/${project.id}/integration`,
            data: { provider, api_key: apiKey },
        })
        if (result.error) {
            setError(result.error)
        } else {
            setApiKey('')
            setSuccess(true)
            load()
        }
    }

    const verify = async () => {
        setVerifying(true)
        setVerifyResult(undefined)
        const result = await http({
            method: APIMethod.post,
            path: `/api/project/${project.id}/integration/verify`,
        })
        setVerifying(false)
        if (result.error) {
            setVerifyResult({ ok: false, message: result.error })
        } else {
            setVerifyResult({ ok: true })
        }
    }

    const remove = async () => {
        setSuccess(false)
        setError(undefined)
        const result = await http({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/integration`,
        })
        if (result.error) {
            setError(result.error)
        } else {
            load()
        }
    }

    if (!integration) return null

    return (
        <div>
            {integration.enabled
                ? <>
                    <Stack direction="horizontal" gap={2} className="my-2">
                        <Badge bg="success">Active</Badge>
                        <span className="text-muted small">{integration.provider_label}</span>
                        {isAdmin && (
                            <Button variant="outline-secondary" size="sm" onClick={verify} disabled={verifying}>
                                {verifying ? <><Spinner size="sm" className="me-1" />Verifying…</> : 'Verify'}
                            </Button>
                        )}
                        {isAdmin && (
                            <Button variant="outline-danger" size="sm" onClick={remove}>
                                Remove
                            </Button>
                        )}
                    </Stack>
                    {verifyResult && (
                        <Alert
                            variant={verifyResult.ok ? 'success' : 'danger'}
                            onClose={() => setVerifyResult(undefined)}
                            dismissible
                        >
                            {verifyResult.ok ? 'Token is valid' : verifyResult.message}
                        </Alert>
                    )}
                </>
                : <span className="text-muted small d-block mb-2">No integration configured</span>
            }

            {isAdmin && (
                <Stack gap={2} style={{ maxWidth: 400 }}>
                    <Form.Select
                        value={provider}
                        onChange={e => setProvider(e.target.value)}
                        size="sm"
                    >
                        {integration.providers.map(p => (
                            <option key={p.value} value={p.value}>{p.label}</option>
                        ))}
                    </Form.Select>
                    <Form.Control
                        type="password"
                        placeholder={integration.enabled ? 'New API key (leave blank to keep current)' : 'API key'}
                        value={apiKey}
                        onChange={e => setApiKey(e.target.value)}
                        size="sm"
                        autoComplete="new-password"
                    />
                    <div>
                        <Button size="sm" onClick={save} disabled={!integration.enabled && !apiKey}>
                            {integration.enabled ? 'Update' : 'Save'}
                        </Button>
                        {success && <span className="text-success small ms-2">Saved</span>}
                    </div>
                </Stack>
            )}

            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </div>
    )
}

export default IntegrationSettings
