import { FC, useEffect, useState } from "react"
import {
    Alert, Badge, Button, Form, ListGroup, ListGroupItem, Spinner, Stack
} from "react-bootstrap"
import Project, { ProjectRole } from "../model/Project"
import { APIMethod, http } from "../Utils/network"
import ErrorAlert from "../UI/ErrorAlert"

// Types

type WebhookEndpoint = {
    id: number
    title: string
    url: string
    has_auth_token: boolean
    signing_secret: string
    template: string
    events: string[]
    is_active: boolean
}

type WebhookForm = {
    title: string
    url: string
    auth_token: string
    template: string
    events: string[]
    is_active: boolean
}

const EMPTY_FORM: WebhookForm = {
    title: '',
    url: '',
    auth_token: '',
    template: '',
    events: [],
    is_active: true,
}

type WebhookSettingsProps = {
    project: Project
}

// Component

const WebhookSettings: FC<WebhookSettingsProps> = ({ project }) => {
    const isAdmin = project.role === ProjectRole.owner || project.role === ProjectRole.admin

    const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([])
    const [availableEvents, setAvailableEvents] = useState<string[]>([])
    const [editingId, setEditingId] = useState<number | 'new' | null>(null)
    const [form, setForm] = useState<WebhookForm>(EMPTY_FORM)
    const [saving, setSaving] = useState(false)
    const [testingId, setTestingId] = useState<number | null>(null)
    const [testResult, setTestResult] = useState<{ id: number; ok: boolean; message?: string } | null>(null)
    const [newSecret, setNewSecret] = useState<string | null>(null)
    const [error, setError] = useState<string>()

    // Loaders

    const load = async () => {
        const result = await http<WebhookEndpoint[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/webhooks`,
        })
        if (result.value) setWebhooks(result.value)
        else setError(result.error)
    }

    const loadEvents = async () => {
        const result = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/webhooks/events`,
        })
        if (result.value) setAvailableEvents(result.value)
    }

    useEffect(() => {
        load()
        if (isAdmin) loadEvents()
    }, [])

    // Form helpers

    const startAdd = () => {
        setForm(EMPTY_FORM)
        setEditingId('new')
        setNewSecret(null)
        setError(undefined)
    }

    const startEdit = (w: WebhookEndpoint) => {
        setForm({
            title: w.title,
            url: w.url,
            auth_token: '',
            template: w.template,
            events: w.events,
            is_active: w.is_active,
        })
        setEditingId(w.id)
        setNewSecret(null)
        setError(undefined)
    }

    const cancel = () => {
        setEditingId(null)
        setError(undefined)
    }

    const toggleEvent = (event: string) => {
        setForm(f => ({
            ...f,
            events: f.events.includes(event)
                ? f.events.filter(e => e !== event)
                : [...f.events, event],
        }))
    }

    // API actions

    const save = async () => {
        if (!form.title.trim() || !form.url.trim()) {
            setError('Title and URL are required.')
            return
        }
        setSaving(true)
        setError(undefined)

        const isNew = editingId === 'new'
        const payload: Record<string, unknown> = {
            title: form.title,
            url: form.url,
            template: form.template,
            events: form.events,
            is_active: form.is_active,
        }
        if (form.auth_token) payload.auth_token = form.auth_token

        const result = await http<WebhookEndpoint>({
            method: isNew ? APIMethod.post : APIMethod.put,
            path: isNew
                ? `/api/project/${project.id}/webhooks`
                : `/api/project/${project.id}/webhooks/${editingId}`,
            data: payload,
        })

        setSaving(false)

        if (result.error) {
            setError(result.error)
            return
        }

        if (isNew && result.value?.signing_secret && result.value.signing_secret !== '••••••••') {
            setNewSecret(result.value.signing_secret)
        }

        setEditingId(null)
        load()
    }

    const remove = async (id: number) => {
        setError(undefined)
        const result = await http({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/webhooks/${id}`,
        })
        if (result.error) setError(result.error)
        else load()
    }

    const verify = async (id: number) => {
        setTestingId(id)
        setTestResult(null)
        const result = await http({
            method: APIMethod.post,
            path: `/api/project/${project.id}/webhooks/${id}/verify`,
        })
        setTestingId(null)
        setTestResult({ id, ok: !result.error, message: result.error })
    }

    // Render

    const isEditing = editingId !== null

    return (
        <div>
            {/* Signing secret reveal — shown once after creation */}
            {newSecret && (
                <Alert
                    variant="success"
                    dismissible
                    onClose={() => setNewSecret(null)}
                    className="mb-3"
                >
                    <Alert.Heading>Webhook created — save your signing secret</Alert.Heading>
                    <p className="mb-1 small text-muted">
                        Use this to verify incoming requests. It won't be shown again.
                    </p>
                    <Stack direction="horizontal" gap={2}>
                        <code style={{ wordBreak: 'break-all' }}>{newSecret}</code>
                        <Button
                            size="sm"
                            variant="outline-success"
                            className="ms-auto"
                            onClick={() => navigator.clipboard.writeText(newSecret)}
                        >
                            Copy
                        </Button>
                    </Stack>
                </Alert>
            )}

            {/* Test result toast */}
            {testResult && (
                <Alert
                    variant={testResult.ok ? 'success' : 'danger'}
                    dismissible
                    onClose={() => setTestResult(null)}
                    className="mb-2"
                >
                    {testResult.ok
                        ? 'Webhook is reachable.'
                        : (testResult.message ?? 'Delivery failed.')}
                </Alert>
            )}

            {/* Webhook list */}
            {webhooks.length > 0 && (
                <ListGroup className="mb-3">
                    {webhooks.map(w => (
                        <ListGroupItem key={w.id}>
                            <Stack direction="horizontal" gap={2} className="flex-wrap">
                                <div className="me-auto">
                                    <Stack direction="horizontal" gap={2} className="mb-1">
                                        <span className="fw-semibold">{w.title}</span>
                                        <Badge bg={w.is_active ? 'success' : 'secondary'}>
                                            {w.is_active ? 'Active' : 'Inactive'}
                                        </Badge>
                                        {w.events.length > 0 && (
                                            <Badge bg="light" text="dark">
                                                {w.events.length} event{w.events.length !== 1 ? 's' : ''}
                                            </Badge>
                                        )}
                                    </Stack>
                                    <div className="text-muted small" style={{ wordBreak: 'break-all' }}>
                                        {w.url}
                                    </div>
                                </div>
                                {isAdmin && (
                                    <Stack direction="horizontal" gap={2}>
                                        <Button
                                            size="sm"
                                            variant="outline-secondary"
                                            onClick={() => verify(w.id)}
                                            disabled={testingId === w.id}
                                        >
                                            {testingId === w.id
                                                ? <Spinner size="sm" />
                                                : 'Verify'
                                            }
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="outline-primary"
                                            onClick={() => startEdit(w)}
                                            disabled={isEditing}
                                        >
                                            Edit
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="outline-danger"
                                            onClick={() => remove(w.id)}
                                            disabled={isEditing}
                                        >
                                            Delete
                                        </Button>
                                    </Stack>
                                )}
                            </Stack>
                        </ListGroupItem>
                    ))}
                </ListGroup>
            )}

            {webhooks.length === 0 && !isEditing && (
                <p className="text-muted small mb-3">No webhooks configured.</p>
            )}

            {/* Add / Edit form */}
            {isEditing && (
                <div className="border rounded-3 p-3 mb-3">
                    <h6 className="mb-3">{editingId === 'new' ? 'Add webhook' : 'Edit webhook'}</h6>

                    <Stack gap={2} style={{ maxWidth: 480 }}>
                        <Form.Group>
                            <Form.Label className="small mb-1">Title</Form.Label>
                            <Form.Control
                                size="sm"
                                placeholder="e.g. Slack #translations"
                                value={form.title}
                                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                            />
                        </Form.Group>

                        <Form.Group>
                            <Form.Label className="small mb-1">Webhook URL</Form.Label>
                            <Form.Control
                                size="sm"
                                placeholder="https://hooks.slack.com/services/…"
                                value={form.url}
                                onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
                            />
                        </Form.Group>

                        <Form.Group>
                            <Form.Label className="small mb-1">
                                Auth token{' '}
                                <span className="text-muted">(optional — sent as Bearer token)</span>
                            </Form.Label>
                            <Form.Control
                                size="sm"
                                type="password"
                                autoComplete="new-password"
                                placeholder={editingId !== 'new' ? 'Leave blank to keep current' : 'Bearer token'}
                                value={form.auth_token}
                                onChange={e => setForm(f => ({ ...f, auth_token: e.target.value }))}
                            />
                        </Form.Group>

                        <Form.Group>
                            <Form.Label className="small mb-1">
                                Message template{' '}
                                <span className="text-muted">(optional — use {'{{token}}'}, {'{{language}}'}, {'{{actor}}'})</span>
                            </Form.Label>
                            <Form.Control
                                size="sm"
                                as="textarea"
                                rows={2}
                                placeholder="e.g. Translation updated: {{token}} ({{language}}) by {{actor}}"
                                value={form.template}
                                onChange={e => setForm(f => ({ ...f, template: e.target.value }))}
                            />
                        </Form.Group>

                        <Form.Group>
                            <Form.Label className="small mb-1">Events</Form.Label>
                            <div style={{ columns: 2 }}>
                                {availableEvents.map(event => (
                                    <Form.Check
                                        key={event}
                                        type="checkbox"
                                        id={`event-${event}`}
                                        label={event}
                                        checked={form.events.includes(event)}
                                        onChange={() => toggleEvent(event)}
                                        className="small"
                                    />
                                ))}
                            </div>
                        </Form.Group>

                        <Form.Check
                            type="switch"
                            id="webhook-active"
                            label="Active"
                            checked={form.is_active}
                            onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                        />

                        <Stack direction="horizontal" gap={2}>
                            <Button size="sm" onClick={save} disabled={saving}>
                                {saving ? <><Spinner size="sm" className="me-1" />Saving…</> : 'Save'}
                            </Button>
                            <Button size="sm" variant="outline-secondary" onClick={cancel} disabled={saving}>
                                Cancel
                            </Button>
                        </Stack>
                    </Stack>
                </div>
            )}

            {/* Add button — only when not already editing */}
            {isAdmin && !isEditing && (
                <Button size="sm" variant="outline-primary" onClick={startAdd}>
                    Add webhook
                </Button>
            )}

            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </div>
    )
}

export default WebhookSettings
