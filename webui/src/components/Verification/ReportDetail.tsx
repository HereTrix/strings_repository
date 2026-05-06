import { FC, useEffect, useRef, useState } from "react"
import { Alert, Badge, Button, Form, Spinner, Stack } from "react-bootstrap"
import Project, { ProjectRole } from "../../types/Project"
import { VerificationComment, VerificationReport, VerificationSuggestion } from "../../types/Verification"
import { APIMethod, http } from "../../utils/network"
import DiffView from "../UI/DiffView"
import ErrorAlert from "../UI/ErrorAlert"

type ReportDetailProps = {
    reportId: number
    project: Project
    onBack: () => void
    onReportUpdated: () => void
}

const SEVERITY_VARIANT: Record<string, string> = {
    ok: 'success',
    warning: 'warning',
    error: 'danger',
}

const STATUS_VARIANT: Record<string, string> = {
    pending: 'secondary',
    running: 'warning',
    complete: 'success',
    failed: 'danger',
}

const ReportDetail: FC<ReportDetailProps> = ({ reportId, project, onBack, onReportUpdated }) => {
    const canEdit = project.role === ProjectRole.owner || project.role === ProjectRole.admin || project.role === ProjectRole.editor

    const [report, setReport] = useState<VerificationReport | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string>()
    const [selected, setSelected] = useState<Record<string, string>>({})
    const [applying, setApplying] = useState(false)
    const [applyError, setApplyError] = useState<string>()
    const [applySuccess, setApplySuccess] = useState<string>()
    const [commentTexts, setCommentTexts] = useState<Record<string, string>>({})
    const [submittingComment, setSubmittingComment] = useState<Record<string, boolean>>({})
    const [localComments, setLocalComments] = useState<Record<string, VerificationComment[]>>({})
    const pollTimer = useRef<number | null>(null)

    const loadReport = async () => {
        const result = await http<VerificationReport>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/verify/${reportId}`,
        })
        if (result.value) {
            setReport(result.value)
            return result.value
        } else {
            setError(result.error)
            return null
        }
    }

    useEffect(() => {
        setLoading(true)
        loadReport().then(r => {
            setLoading(false)
            if (r && (r.status === 'pending' || r.status === 'running')) {
                pollTimer.current = window.setInterval(async () => {
                    const updated = await loadReport()
                    if (updated && updated.status !== 'pending' && updated.status !== 'running') {
                        if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null }
                    }
                }, 5000)
            }
        })
        return () => { if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null } }
    }, [reportId])

    const suggestionKey = (s: VerificationSuggestion) => `${s.token_id}:${s.plural_form ?? ''}`

    const toggleSelect = (s: VerificationSuggestion) => {
        const key = suggestionKey(s)
        setSelected(prev => {
            if (key in prev) {
                const next = { ...prev }
                delete next[key]
                return next
            }
            return { ...prev, [key]: s.suggestion }
        })
    }

    const applySelected = async () => {
        if (!report) return
        setApplying(true)
        setApplyError(undefined)
        setApplySuccess(undefined)
        const suggestions = Object.entries(selected).map(([key, text]) => {
            const [token_id, plural_form] = key.split(':')
            return { token_id: parseInt(token_id), plural_form: plural_form || null, text }
        })
        const result = await http<{ applied: number; errors: string[] }>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/verify/${reportId}/apply`,
            data: { suggestions },
        })
        setApplying(false)
        if (result.value) {
            setApplySuccess(`${result.value.applied} suggestion${result.value.applied !== 1 ? 's' : ''} applied`)
            setSelected({})
            onReportUpdated()
            loadReport()
        } else {
            setApplyError(result.error)
        }
    }

    const addComment = async (s: VerificationSuggestion) => {
        const key = suggestionKey(s)
        const text = commentTexts[key]?.trim()
        if (!text || !report) return
        setSubmittingComment(prev => ({ ...prev, [key]: true }))
        const result = await http<VerificationComment>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/verify/${reportId}/comments`,
            data: { token_id: s.token_id, token_key: s.token_key, plural_form: s.plural_form ?? '', text },
        })
        setSubmittingComment(prev => ({ ...prev, [key]: false }))
        if (result.value) {
            setLocalComments(prev => ({ ...prev, [key]: [...(prev[key] ?? []), result.value!] }))
            setCommentTexts(prev => ({ ...prev, [key]: '' }))
        }
    }

    if (loading) return <Spinner />
    if (!report) return <ErrorAlert error={error ?? 'Report not found'} onClose={onBack} />

    const commentsForSuggestion = (s: VerificationSuggestion): VerificationComment[] => {
        const key = suggestionKey(s)
        const fromReport = report.comments?.filter(c => c.token_id === s.token_id && c.plural_form === (s.plural_form ?? '')) ?? []
        return [...fromReport, ...(localComments[key] ?? [])]
    }

    return (
        <div className="mt-3">
            <Stack direction="horizontal" gap={2} className="mb-3">
                <Button variant="link" className="p-0" onClick={onBack}>← Back</Button>
                <span className="fw-semibold">
                    {report.mode === 'source_quality' ? 'Source Quality' : 'Translation Accuracy'}
                    {report.target_language && <span className="text-muted ms-1">→ {report.target_language}</span>}
                </span>
                <Badge bg={STATUS_VARIANT[report.status] ?? 'secondary'}>{report.status}</Badge>
                {report.is_readonly && <Badge bg="secondary">Read-only</Badge>}
                {report.status === 'complete' && report.summary && (
                    <Stack direction="horizontal" gap={1}>
                        <Badge bg="success">ok/{report.summary.ok}</Badge>
                        <Badge bg="warning" text="dark">warn/{report.summary.warning}</Badge>
                        <Badge bg="danger">err/{report.summary.error}</Badge>
                    </Stack>
                )}
                <span className="text-muted small ms-auto">{new Date(report.created_at).toLocaleDateString()}</span>
            </Stack>

            {report.status === 'failed' && (
                <Alert variant="danger">{report.error_message ?? 'Verification failed'}</Alert>
            )}

            {(report.status === 'pending' || report.status === 'running') && (
                <Stack direction="horizontal" gap={2}>
                    <Spinner size="sm" />
                    <span className="text-muted">Verification in progress…</span>
                </Stack>
            )}

            {report.status === 'complete' && report.result?.results && (
                <>
                    {canEdit && !report.is_readonly && (
                        <Stack direction="horizontal" gap={2} className="mb-3">
                            <Button
                                size="sm"
                                disabled={Object.keys(selected).length === 0 || applying}
                                onClick={applySelected}
                            >
                                {applying ? <><Spinner size="sm" className="me-1" />Applying…</> : `Apply selected (${Object.keys(selected).length})`}
                            </Button>
                            {applySuccess && <span className="text-success small">{applySuccess}</span>}
                            {applyError && <span className="text-danger small">{applyError}</span>}
                        </Stack>
                    )}

                    {report.result.results.map((s, idx) => {
                        const key = suggestionKey(s)
                        const comments = commentsForSuggestion(s)
                        return (
                            <div key={idx} className="border rounded p-2 mb-2">
                                <Stack direction="horizontal" gap={2} className="mb-1">
                                    <Badge bg={SEVERITY_VARIANT[s.severity] ?? 'secondary'}>
                                        {s.severity.toUpperCase()}
                                    </Badge>
                                    <code className="small">{s.token_key}</code>
                                    {s.plural_form && <span className="text-muted small">({s.plural_form})</span>}
                                    {canEdit && !report.is_readonly && s.severity !== 'ok' && (
                                        <Form.Check
                                            className="ms-auto"
                                            checked={key in selected}
                                            onChange={() => toggleSelect(s)}
                                            label="Select"
                                        />
                                    )}
                                </Stack>

                                <div className="mb-1">
                                    <DiffView base={s.current} next={s.suggestion} />
                                </div>

                                <div className="text-muted small mb-2">{s.reason}</div>

                                {key in selected && !report.is_readonly && (
                                    <Form.Control
                                        size="sm"
                                        type="text"
                                        value={selected[key]}
                                        onChange={e => setSelected(prev => ({ ...prev, [key]: e.target.value }))}
                                        className="mb-2"
                                    />
                                )}

                                {comments.length > 0 && (
                                    <div className="mb-2">
                                        {comments.map((c, ci) => (
                                            <div key={ci} className="small text-muted border-start ps-2 mb-1">
                                                <span className="fw-semibold">{c.author}</span>: {c.text}
                                                <span className="ms-2" style={{ fontSize: '0.75em' }}>{new Date(c.created_at).toLocaleString()}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <Stack direction="horizontal" gap={2}>
                                    <Form.Control
                                        size="sm"
                                        type="text"
                                        placeholder="Add comment…"
                                        value={commentTexts[key] ?? ''}
                                        onChange={e => setCommentTexts(prev => ({ ...prev, [key]: e.target.value }))}
                                        style={{ maxWidth: 300 }}
                                    />
                                    <Button
                                        size="sm"
                                        variant="outline-secondary"
                                        disabled={!commentTexts[key]?.trim() || submittingComment[key]}
                                        onClick={() => addComment(s)}
                                    >
                                        {submittingComment[key] ? <Spinner size="sm" /> : 'Add comment'}
                                    </Button>
                                </Stack>
                            </div>
                        )
                    })}
                </>
            )}
        </div>
    )
}

export default ReportDetail
