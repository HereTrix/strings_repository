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
    endpoint_url?: string
    payload_template?: string
    response_path?: string
    auth_header?: string
}

type AIPreset = {
    label: string
    endpoint_url: string
    payload_template: string
    response_path: string
    auth_header: string
}

const AI_PRESETS: AIPreset[] = [
    {
        label: 'OpenAI / DeepSeek',
        endpoint_url: 'https://api.openai.com/v1/chat/completions',
        payload_template: JSON.stringify({
            model: 'gpt-4o-mini',
            messages: [
                { role: 'system', content: 'Translate to {{target_lang}}. Return only the translation.' },
                { role: 'user', content: '{{text}}' },
            ],
        }, null, 2),
        response_path: 'choices.0.message.content',
        auth_header: 'Authorization',
    },
    {
        label: 'Claude',
        endpoint_url: 'https://api.anthropic.com/v1/messages',
        payload_template: JSON.stringify({
            model: 'claude-haiku-4-5-20251001',
            max_tokens: 1024,
            system: 'Translate to {{target_lang}}. Return only the translation.',
            messages: [{ role: 'user', content: '{{text}}' }],
        }, null, 2),
        response_path: 'content.0.text',
        auth_header: 'x-api-key',
    },
    {
        label: 'Ollama',
        endpoint_url: 'http://localhost:11434/api/generate',
        payload_template: JSON.stringify({
            model: 'llama3',
            prompt: 'Translate the following to {{target_lang}}, return only the translation: {{text}}',
            stream: false,
        }, null, 2),
        response_path: 'response',
        auth_header: 'Authorization',
    },
]

type IntegrationSettingsProps = {
    project: Project
}

const IntegrationSettings: FC<IntegrationSettingsProps> = ({ project }) => {
    const isAdmin = project.role === ProjectRole.owner || project.role === ProjectRole.admin

    const [integration, setIntegration] = useState<Integration>()
    const [provider, setProvider] = useState('')
    const [apiKey, setApiKey] = useState('')
    const [endpointUrl, setEndpointUrl] = useState('')
    const [payloadTemplate, setPayloadTemplate] = useState('')
    const [responsePath, setResponsePath] = useState('')
    const [authHeader, setAuthHeader] = useState('Authorization')
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
            if (result.value.provider === 'ai') {
                setEndpointUrl(result.value.endpoint_url ?? '')
                setPayloadTemplate(result.value.payload_template ?? '')
                setResponsePath(result.value.response_path ?? '')
                setAuthHeader(result.value.auth_header ?? 'Authorization')
            }
        }
    }

    useEffect(() => {
        load()
    }, [])

    const applyPreset = (preset: AIPreset) => {
        setEndpointUrl(preset.endpoint_url)
        setPayloadTemplate(preset.payload_template)
        setResponsePath(preset.response_path)
        setAuthHeader(preset.auth_header)
    }

    const save = async () => {
        setSuccess(false)
        setError(undefined)
        const data: Record<string, string> = { provider, api_key: apiKey }
        if (provider === 'ai') {
            data.endpoint_url = endpointUrl
            data.payload_template = payloadTemplate
            data.response_path = responsePath
            data.auth_header = authHeader
        }
        const result = await http({
            method: APIMethod.post,
            path: `/api/project/${project.id}/integration`,
            data,
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
                <Stack gap={2} style={{ maxWidth: 500 }}>
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
                    {provider === 'ai' && (
                        <>
                            <div>
                                <Form.Label className="small mb-1">Presets</Form.Label>
                                <Stack direction="horizontal" gap={1} className="flex-wrap">
                                    {AI_PRESETS.map(preset => (
                                        <Button
                                            key={preset.label}
                                            variant="outline-secondary"
                                            size="sm"
                                            onClick={() => applyPreset(preset)}
                                        >
                                            {preset.label}
                                        </Button>
                                    ))}
                                </Stack>
                            </div>
                            <Form.Control
                                type="text"
                                placeholder="Endpoint URL"
                                value={endpointUrl}
                                onChange={e => setEndpointUrl(e.target.value)}
                                size="sm"
                            />
                            <Form.Control
                                type="text"
                                placeholder="Auth header name (e.g. Authorization or x-api-key)"
                                value={authHeader}
                                onChange={e => setAuthHeader(e.target.value)}
                                size="sm"
                            />
                            <Form.Control
                                as="textarea"
                                rows={8}
                                placeholder={'Payload template (JSON)\nUse {{text}}, {{target_lang}}, {{source_lang}}'}
                                value={payloadTemplate}
                                onChange={e => setPayloadTemplate(e.target.value)}
                                size="sm"
                                style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
                            />
                            <Form.Control
                                type="text"
                                placeholder="Response path (e.g. choices.0.message.content)"
                                value={responsePath}
                                onChange={e => setResponsePath(e.target.value)}
                                size="sm"
                            />
                        </>
                    )}
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
