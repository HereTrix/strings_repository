// Copyright (c) StringsRepository Contributors
// SPDX-License-Identifier: MIT

import { FC, useEffect, useState } from "react"
import { Alert, Button, Form, Spinner, Stack } from "react-bootstrap"
import Project, { ProjectRole } from "../../types/Project"
import { LiveBundleSettings as LiveBundleSettingsData } from "../../types/LiveBundle"
import { APIMethod, http } from "../../utils/network"
import ErrorAlert from "../UI/ErrorAlert"

type LiveBundleSettingsProps = {
    project: Project
}

const LiveBundleSettingsPanel: FC<LiveBundleSettingsProps> = ({ project }) => {
    const isAdmin = project.role === ProjectRole.owner || project.role === ProjectRole.admin
    const canViewToken = isAdmin || project.role === ProjectRole.editor

    const [settings, setSettings] = useState<LiveBundleSettingsData>()
    const [loading, setLoading] = useState(true)
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState<string>()

    const load = async () => {
        setLoading(true)
        const result = await http<LiveBundleSettingsData>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/live-bundle`,
        })
        setLoading(false)
        if (result.value) setSettings(result.value)
        else setError(result.error)
    }

    useEffect(() => { load() }, [project.id])

    const enable = async () => {
        setBusy(true)
        setError(undefined)
        const result = await http<LiveBundleSettingsData>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/live-bundle`,
        })
        setBusy(false)
        if (result.value) setSettings(result.value)
        else setError(result.error)
    }

    const disable = async () => {
        setBusy(true)
        setError(undefined)
        const result = await http<LiveBundleSettingsData>({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/live-bundle`,
        })
        setBusy(false)
        if (result.value) setSettings(result.value)
        else setError(result.error)
    }

    const regenerate = async () => {
        setBusy(true)
        setError(undefined)
        const result = await http<LiveBundleSettingsData>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/live-bundle/regenerate`,
        })
        setBusy(false)
        if (result.value) setSettings(result.value)
        else setError(result.error)
    }

    if (loading) return <Spinner size="sm" />

    return (
        <Stack gap={2}>
            <Form.Check
                type="switch"
                id="live-bundle-toggle"
                label="Enable live bundle serving"
                checked={settings?.enabled ?? false}
                disabled={!isAdmin || busy}
                onChange={(e) => e.target.checked ? enable() : disable()}
            />
            <Form.Text className="text-muted">
                When enabled, client applications can fetch this project's currently live bundle
                over a public URL using the access token below.
            </Form.Text>

            {settings?.enabled && canViewToken && (
                <Stack direction="horizontal" gap={2} className="align-items-center">
                    <code className="border rounded px-2 py-1">{settings.token}</code>
                    {isAdmin && (
                        <Button
                            size="sm"
                            variant="outline-secondary"
                            disabled={busy}
                            onClick={regenerate}
                        >
                            Regenerate token
                        </Button>
                    )}
                </Stack>
            )}

            {settings?.enabled && !canViewToken && (
                <Alert variant="info" className="py-1 px-2 mb-0">
                    Live bundle serving is enabled. Ask a project admin or editor for the access token.
                </Alert>
            )}

            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </Stack>
    )
}

export default LiveBundleSettingsPanel
