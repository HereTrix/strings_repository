import { FC, useEffect, useState } from "react"
import { Alert, Button, Form, Modal, Spinner, Stack } from "react-bootstrap"
import Project from "../../types/Project"
import Scope from "../../types/Scope"
import { MODE_CHECKS, VerificationMode, VerificationReport } from "../../types/Verification"
import { APIMethod, http } from "../../utils/network"

type RunVerificationModalProps = {
    show: boolean
    project: Project
    onHide: () => void
    onSuccess: (report: VerificationReport) => void
}

const RunVerificationModal: FC<RunVerificationModalProps> = ({ show, project, onHide, onSuccess }) => {
    const [mode, setMode] = useState<VerificationMode>('source_quality')
    const [targetLanguage, setTargetLanguage] = useState('')
    const [scopeId, setScopeId] = useState('')
    const [tags, setTags] = useState<string[]>([])
    const [newOnly, setNewOnly] = useState(false)
    const [checks, setChecks] = useState<string[]>(MODE_CHECKS.source_quality.map(c => c.key))
    const [scopes, setScopes] = useState<Scope[]>([])
    const [availableTags, setAvailableTags] = useState<string[]>([])
    const [estimatedCount, setEstimatedCount] = useState<number | null>(null)
    const [estimating, setEstimating] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string>()

    useEffect(() => {
        http<Scope[]>({ method: APIMethod.get, path: `/api/project/${project.id}/scopes` })
            .then(r => { if (r.value) setScopes(r.value) })
        http<string[]>({ method: APIMethod.get, path: `/api/project/${project.id}/tags` })
            .then(r => { if (r.value) setAvailableTags(r.value) })
    }, [])

    useEffect(() => {
        setChecks(MODE_CHECKS[mode].map(c => c.key))
        setEstimatedCount(null)
    }, [mode])

    const toggleCheck = (key: string) => {
        setChecks(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key])
    }

    const toggleTag = (tag: string) => {
        setTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag])
    }

    const estimate = async () => {
        setEstimating(true)
        setEstimatedCount(null)
        const params = new URLSearchParams({ mode })
        if (targetLanguage) params.set('target_language', targetLanguage)
        if (scopeId) params.set('scope_id', scopeId)
        if (tags.length) params.set('tags', tags.join(','))
        if (newOnly) params.set('new_only', 'true')
        const result = await http<{ count: number }>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/verify/count?${params}`,
        })
        setEstimating(false)
        if (result.value !== undefined) setEstimatedCount(result.value.count)
    }

    const submit = async () => {
        setSubmitting(true)
        setError(undefined)
        const result = await http<VerificationReport>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/verify`,
            data: {
                mode,
                target_language: targetLanguage || undefined,
                scope_id: scopeId || undefined,
                tags,
                new_only: newOnly,
                checks,
            },
        })
        setSubmitting(false)
        if (result.value) {
            onSuccess(result.value)
        } else {
            setError(result.error ?? 'Unknown error')
        }
    }

    const canRun = checks.length > 0 && (mode === 'source_quality' || targetLanguage !== '') && estimatedCount !== 0

    return (
        <Modal show={show} onHide={onHide} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Run Verification</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Stack gap={3}>
                    <div>
                        <Form.Label className="fw-semibold">Mode</Form.Label>
                        <div>
                            <Form.Check
                                inline type="radio" label="Source Quality" name="mode"
                                checked={mode === 'source_quality'}
                                onChange={() => setMode('source_quality')}
                            />
                            <Form.Check
                                inline type="radio" label="Translation Accuracy" name="mode"
                                checked={mode === 'translation_accuracy'}
                                onChange={() => setMode('translation_accuracy')}
                            />
                        </div>
                    </div>

                    {mode === 'translation_accuracy' && (
                        <div>
                            <Form.Label className="fw-semibold">Target Language <span className="text-danger">*</span></Form.Label>
                            <Form.Select size="sm" value={targetLanguage} onChange={e => setTargetLanguage(e.target.value)} style={{ maxWidth: 300 }}>
                                <option value="">— Select language —</option>
                                {project.languages.map(lang => (
                                    <option key={lang.code} value={lang.code}>{lang.name} ({lang.code})</option>
                                ))}
                            </Form.Select>
                        </div>
                    )}

                    <div>
                        <Form.Label className="fw-semibold">Scope</Form.Label>
                        <Form.Select size="sm" value={scopeId} onChange={e => setScopeId(e.target.value)} style={{ maxWidth: 300 }}>
                            <option value="">All scopes</option>
                            {scopes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                        </Form.Select>
                    </div>

                    {availableTags.length > 0 && (
                        <div>
                            <Form.Label className="fw-semibold">Tags</Form.Label>
                            <Stack direction="horizontal" gap={1} className="flex-wrap">
                                {availableTags.map(tag => (
                                    <Button
                                        key={tag}
                                        size="sm"
                                        variant={tags.includes(tag) ? 'primary' : 'outline-secondary'}
                                        onClick={() => toggleTag(tag)}
                                    >
                                        {tag}
                                    </Button>
                                ))}
                            </Stack>
                        </div>
                    )}

                    {mode === 'translation_accuracy' && (
                        <Form.Check
                            label="New translations only"
                            checked={newOnly}
                            onChange={e => setNewOnly(e.target.checked)}
                        />
                    )}

                    <div>
                        <Stack direction="horizontal" gap={2} className="mb-1">
                            <Form.Label className="fw-semibold mb-0">Checks</Form.Label>
                            <Button variant="link" size="sm" className="p-0" onClick={() => setChecks(MODE_CHECKS[mode].map(c => c.key))}>Select all</Button>
                            <Button variant="link" size="sm" className="p-0" onClick={() => setChecks([])}>Deselect all</Button>
                        </Stack>
                        {MODE_CHECKS[mode].map(check => (
                            <Form.Check
                                key={check.key}
                                label={check.label}
                                checked={checks.includes(check.key)}
                                onChange={() => toggleCheck(check.key)}
                            />
                        ))}
                    </div>

                    <Stack direction="horizontal" gap={2} className="align-items-center">
                        <Button
                            variant="outline-secondary"
                            size="sm"
                            onClick={estimate}
                            disabled={estimating || (mode === 'translation_accuracy' && !targetLanguage)}
                        >
                            {estimating ? <><Spinner size="sm" className="me-1" />Estimating…</> : 'Estimate strings'}
                        </Button>
                        {estimatedCount !== null && estimatedCount > 0 && (
                            <span className="text-muted small">~{estimatedCount} strings will be sent to the AI</span>
                        )}
                        {estimatedCount === 0 && (
                            <Alert variant="warning" className="mb-0 py-1 px-2 small">No strings match the selected filters</Alert>
                        )}
                    </Stack>

                    {error && <Alert variant="danger">{error}</Alert>}
                </Stack>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide}>Cancel</Button>
                <Button onClick={submit} disabled={!canRun || submitting}>
                    {submitting ? <><Spinner size="sm" className="me-1" />Running…</> : 'Run Verification'}
                </Button>
            </Modal.Footer>
        </Modal>
    )
}

export default RunVerificationModal
