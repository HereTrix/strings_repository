import { FC, useEffect, useState } from "react"
import { Badge, Button, Collapse, Form, Stack } from "react-bootstrap"
import Project, { ProjectRole } from "../../types/Project"
import { AIProvider } from "../../types/Verification"
import { APIMethod, http } from "../../utils/network"
import ErrorAlert from "../UI/ErrorAlert"

type AIPreset = {
    label: string
    provider_type: string
    endpoint_url: string
    model_name: string
    request_timeout: number
}

const AI_PRESETS: AIPreset[] = [
    { label: 'OpenAI', provider_type: 'openai', endpoint_url: '', model_name: 'gpt-4o-mini', request_timeout: 120 },
    { label: 'Claude', provider_type: 'anthropic', endpoint_url: '', model_name: 'claude-haiku-4-5-20251001', request_timeout: 120 },
    { label: 'Ollama', provider_type: 'openai', endpoint_url: 'http://localhost:11434/v1/chat/completions', model_name: 'llama3', request_timeout: 300 },
]

type AIProviderSettingsProps = {
    project: Project
    onProviderChange?: () => void
}

const AIProviderSettings: FC<AIProviderSettingsProps> = ({ project, onProviderChange }) => {
    const isAdmin = project.role === ProjectRole.owner || project.role === ProjectRole.admin

    const [provider, setProvider] = useState<AIProvider>()
    const [providerType, setProviderType] = useState('')
    const [apiKey, setApiKey] = useState('')
    const [endpointUrl, setEndpointUrl] = useState('')
    const [modelName, setModelName] = useState('')
    const [requestTimeout, setRequestTimeout] = useState(120)
    const [translationInstructions, setTranslationInstructions] = useState('')
    const [verificationInstructions, setVerificationInstructions] = useState('')
    const [glossaryExtractionInstructions, setGlossaryExtractionInstructions] = useState('')
    const [translationMemoryInstructions, setTranslationMemoryInstructions] = useState('')
    const [translationOpen, setTranslationOpen] = useState(false)
    const [verificationOpen, setVerificationOpen] = useState(false)
    const [glossaryOpen, setGlossaryOpen] = useState(false)
    const [translationMemoryOpen, setTranslationMemoryOpen] = useState(false)
    const [error, setError] = useState<string>()
    const [success, setSuccess] = useState(false)

    const load = async () => {
        const result = await http<AIProvider>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/ai-provider`,
        })
        if (result.value) {
            setProvider(result.value)
            if (result.value.enabled) {
                setProviderType(result.value.provider_type ?? '')
                setEndpointUrl(result.value.endpoint_url ?? '')
                setModelName(result.value.model_name ?? '')
                setRequestTimeout(result.value.request_timeout ?? 120)
                setTranslationInstructions(result.value.translation_instructions ?? '')
                setVerificationInstructions(result.value.verification_instructions ?? '')
                setGlossaryExtractionInstructions(result.value.glossary_extraction_instructions ?? '')
                setTranslationMemoryInstructions(result.value.translation_memory_instructions ?? '')
                setTranslationOpen(!!(result.value.translation_instructions))
                setVerificationOpen(!!(result.value.verification_instructions))
                setGlossaryOpen(!!(result.value.glossary_extraction_instructions))
                setTranslationMemoryOpen(!!(result.value.translation_memory_instructions))
            } else if (result.value.providers.length > 0) {
                setProviderType(result.value.providers[0].value)
            }
        }
    }

    useEffect(() => {
        load()
    }, [])

    const applyPreset = (preset: AIPreset) => {
        setProviderType(preset.provider_type)
        setEndpointUrl(preset.endpoint_url)
        setModelName(preset.model_name)
        setRequestTimeout(preset.request_timeout)
    }

    const save = async () => {
        setSuccess(false)
        setError(undefined)
        const result = await http({
            method: APIMethod.post,
            path: `/api/project/${project.id}/ai-provider`,
            data: {
                provider_type: providerType,
                api_key: apiKey,
                model_name: modelName,
                endpoint_url: endpointUrl,
                request_timeout: requestTimeout,
                translation_instructions: translationInstructions,
                verification_instructions: verificationInstructions,
                glossary_extraction_instructions: glossaryExtractionInstructions,
                translation_memory_instructions: translationMemoryInstructions,
            },
        })
        if (result.error) {
            setError(result.error)
        } else {
            setApiKey('')
            setSuccess(true)
            load()
            onProviderChange?.()
        }
    }

    const remove = async () => {
        setSuccess(false)
        setError(undefined)
        const result = await http({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/ai-provider`,
        })
        if (result.error) {
            setError(result.error)
        } else {
            load()
            onProviderChange?.()
        }
    }

    if (!provider) return null

    return (
        <div>
            {provider.enabled
                ? <>
                    <Stack direction="horizontal" gap={2} className="my-2">
                        <Badge bg="success">Active</Badge>
                        <span className="text-muted small">{provider.provider_label}</span>
                        {provider.model_name && (
                            <span className="text-muted small">{provider.model_name}</span>
                        )}
                        {isAdmin && (
                            <Button variant="outline-danger" size="sm" onClick={remove}>
                                Remove
                            </Button>
                        )}
                    </Stack>
                </>
                : <span className="text-muted small d-block mb-2">No AI provider configured</span>
            }

            {isAdmin && (
                <Stack gap={2} style={{ maxWidth: 500 }}>
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
                    <Form.Select
                        value={providerType}
                        onChange={e => setProviderType(e.target.value)}
                        size="sm"
                    >
                        {provider.providers.map(p => (
                            <option key={p.value} value={p.value}>{p.label}</option>
                        ))}
                    </Form.Select>
                    <Form.Control
                        type="text"
                        placeholder="Model name (e.g. gpt-4o-mini)"
                        value={modelName}
                        onChange={e => setModelName(e.target.value)}
                        size="sm"
                    />
                    <Form.Control
                        type="text"
                        placeholder="Endpoint URL (leave blank for default)"
                        value={endpointUrl}
                        onChange={e => setEndpointUrl(e.target.value)}
                        size="sm"
                    />
                    <Form.Control
                        type="number"
                        placeholder="Request timeout (seconds)"
                        value={requestTimeout}
                        onChange={e => setRequestTimeout(Number(e.target.value))}
                        size="sm"
                        min={1}
                    />
                    <div>
                        <button
                            type="button"
                            className="btn btn-link btn-sm p-0 text-decoration-none d-flex align-items-center gap-2"
                            onClick={() => setTranslationOpen(o => !o)}
                            aria-expanded={translationOpen}
                        >
                            <span className="small">Translation instructions</span>
                            {translationInstructions && <Badge bg="secondary" pill>Custom</Badge>}
                            <span className="text-muted" style={{ fontSize: '0.6rem' }}>{translationOpen ? '▲' : '▼'}</span>
                        </button>
                        <Collapse in={translationOpen}>
                            <div className="mt-2">
                                <Form.Control
                                    as="textarea"
                                    rows={3}
                                    placeholder="Translate to the target language."
                                    value={translationInstructions}
                                    onChange={e => setTranslationInstructions(e.target.value)}
                                    size="sm"
                                />
                                <Form.Text className="text-muted">
                                    Replaces the default translation directive. Leave blank to use the default.
                                    Available variable: <code>{'{target_lang}'}</code> — replaced with the target language name at runtime.<br />
                                    Example: <em>"You are a professional legal translator. Translate to {'{target_lang}'} using formal register."</em>
                                </Form.Text>
                            </div>
                        </Collapse>
                    </div>
                    <div>
                        <button
                            type="button"
                            className="btn btn-link btn-sm p-0 text-decoration-none d-flex align-items-center gap-2"
                            onClick={() => setVerificationOpen(o => !o)}
                            aria-expanded={verificationOpen}
                        >
                            <span className="small">Verification instructions</span>
                            {verificationInstructions && <Badge bg="secondary" pill>Custom</Badge>}
                            <span className="text-muted" style={{ fontSize: '0.6rem' }}>{verificationOpen ? '▲' : '▼'}</span>
                        </button>
                        <Collapse in={verificationOpen}>
                            <div className="mt-2">
                                <Form.Control
                                    as="textarea"
                                    rows={3}
                                    placeholder="You are a translation quality reviewer."
                                    value={verificationInstructions}
                                    onChange={e => setVerificationInstructions(e.target.value)}
                                    size="sm"
                                />
                                <Form.Text className="text-muted">
                                    Replaces the default reviewer role. Leave blank to use the default.
                                    No variables available — write plain instructions only.<br />
                                    Example: <em>"You are a senior editor for a children's book publisher. Review for age-appropriate language."</em>
                                </Form.Text>
                            </div>
                        </Collapse>
                    </div>
                    <div>
                        <button
                            type="button"
                            className="btn btn-link btn-sm p-0 text-decoration-none d-flex align-items-center gap-2"
                            onClick={() => setGlossaryOpen(o => !o)}
                            aria-expanded={glossaryOpen}
                        >
                            <span className="small">Glossary extraction instructions</span>
                            {glossaryExtractionInstructions && <Badge bg="secondary" pill>Custom</Badge>}
                            <span className="text-muted" style={{ fontSize: '0.6rem' }}>{glossaryOpen ? '▲' : '▼'}</span>
                        </button>
                        <Collapse in={glossaryOpen}>
                            <div className="mt-2">
                                <Form.Control
                                    as="textarea"
                                    rows={3}
                                    placeholder="You are a localization expert."
                                    value={glossaryExtractionInstructions}
                                    onChange={e => setGlossaryExtractionInstructions(e.target.value)}
                                    size="sm"
                                />
                                <Form.Text className="text-muted">
                                    Replaces the default glossary extraction role. Leave blank to use the default.
                                    No variables available — write plain instructions only.<br />
                                    Example: <em>"You are a medical terminology expert. Focus on clinical terms, drug names, and anatomical vocabulary."</em>
                                </Form.Text>
                            </div>
                        </Collapse>
                    </div>
                    <div>
                        <button
                            type="button"
                            className="btn btn-link btn-sm p-0 text-decoration-none d-flex align-items-center gap-2"
                            onClick={() => setTranslationMemoryOpen(o => !o)}
                            aria-expanded={translationMemoryOpen}
                        >
                            <span className="small">Translation memory instructions</span>
                            {translationMemoryInstructions && <Badge bg="secondary" pill>Custom</Badge>}
                            <span className="text-muted" style={{ fontSize: '0.6rem' }}>{translationMemoryOpen ? '▲' : '▼'}</span>
                        </button>
                        <Collapse in={translationMemoryOpen}>
                            <div className="mt-2">
                                <Form.Control
                                    as="textarea"
                                    rows={3}
                                    placeholder="You are a translation expert."
                                    value={translationMemoryInstructions}
                                    onChange={e => setTranslationMemoryInstructions(e.target.value)}
                                    size="sm"
                                />
                                <Form.Text className="text-muted">
                                    Replaces the default translation memory ranking role. Leave blank to use the default.
                                    No variables available — write plain instructions only.<br />
                                    Example: <em>"You are a legal translation specialist. Rank candidates by formal register and terminology consistency."</em>
                                </Form.Text>
                            </div>
                        </Collapse>
                    </div>
                    <Form.Control
                        type="password"
                        placeholder={provider.enabled ? 'New API key (leave blank to keep current)' : 'API key'}
                        value={apiKey}
                        onChange={e => setApiKey(e.target.value)}
                        size="sm"
                        autoComplete="new-password"
                    />
                    <div>
                        <Button size="sm" onClick={save} disabled={!provider.enabled && !apiKey}>
                            {provider.enabled ? 'Update' : 'Save'}
                        </Button>
                        {success && <span className="text-success small ms-2">Saved</span>}
                    </div>
                </Stack>
            )}

            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </div>
    )
}

export default AIProviderSettings
