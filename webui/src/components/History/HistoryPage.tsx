import fileDownload from "js-file-download"
import { FC, JSX, useState } from "react"
import { Badge, Button, Container, Form, Spinner, Stack, Table } from "react-bootstrap"
import { APIMethod, download, http } from "../Utils/network"
import DiffView from "../UI/DiffView"
import ErrorAlert from "../UI/ErrorAlert"
import Project from "../model/Project"

type HistoryPageProps = {
    project: Project
}

interface HistoryRecord {
    updated_at: string
    language: string
    token: string
    editor: string
    status: string
    old_value: string | undefined
    new_value: string
}

const STATUS_VARIANT: Record<string, string> = {
    approved: 'success',
    in_review: 'warning',
    new: 'secondary',
}

const formatDate = (iso: string) =>
    new Date(iso).toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
    })

const HistoryPage: FC<HistoryPageProps> = ({ project }): JSX.Element => {
    const [error, setError] = useState<string | undefined>()
    const [data, setData] = useState<Map<string, HistoryRecord[]> | undefined>()
    const [loading, setLoading] = useState(false)
    const [dateFrom, setDateFrom] = useState<string | undefined>()
    const [dateTo, setDateTo] = useState<string | undefined>()

    const params = () => {
        const p: Record<string, string> = {}
        if (dateFrom) p.from = dateFrom
        if (dateTo) p.to = dateTo
        return p
    }

    const loadHistory = async () => {
        setLoading(true)
        setError(undefined)

        const result = await http<HistoryRecord[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/history`,
            params: params(),
        })

        setLoading(false)

        if (result.value) {
            const grouped = new Map<string, HistoryRecord[]>()
            for (const record of result.value) {
                const group = grouped.get(record.token) ?? []
                group.push(record)
                grouped.set(record.token, group)
            }
            setData(grouped)
        } else {
            setError(result.error)
        }
    }

    const exportHistory = async () => {
        const result = await download({
            method: APIMethod.get,
            path: `/api/project/${project.id}/history/export`,
            params: params(),
        })
        if (result.value) {
            fileDownload(result.value.content, result.value.name)
        } else {
            setError(result.error)
        }
    }

    return (
        <Container className="mt-3">
            <Stack direction="horizontal" gap={2} className="mb-3 align-items-end flex-wrap">
                <Stack direction="horizontal" gap={2} className="align-items-end flex-wrap">
                    <div>
                        <Form.Label className="mb-1 small text-muted">From</Form.Label>
                        <Form.Control
                            type="date"
                            size="sm"
                            onChange={(e) => setDateFrom(e.target.value || undefined)}
                        />
                    </div>
                    <div>
                        <Form.Label className="mb-1 small text-muted">To</Form.Label>
                        <Form.Control
                            type="date"
                            size="sm"
                            onChange={(e) => setDateTo(e.target.value || undefined)}
                        />
                    </div>
                    <Button size="sm" onClick={loadHistory} disabled={loading}>
                        {loading ? <><Spinner size="sm" className="me-1" />Loading…</> : 'Load'}
                    </Button>
                </Stack>
                <Button
                    variant="outline-secondary"
                    size="sm"
                    className="ms-auto"
                    onClick={exportHistory}
                >
                    Export history
                </Button>
            </Stack>

            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}

            {data && data.size === 0 && (
                <p className="text-muted text-center py-4">No history found for the selected period.</p>
            )}

            {data && [...data.entries()].map(([token, records]) => (
                <div key={token} className="mb-4">
                    <h6 className="fw-semibold mb-2 pb-1 border-bottom">{token}</h6>
                    <Table size="sm" hover responsive className="mb-0">
                        <thead className="table-light">
                            <tr>
                                <th>Date</th>
                                <th>Language</th>
                                <th>Change</th>
                                <th>Editor</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {records.map((record) => (
                                <tr key={record.token + record.updated_at}>
                                    <td className="text-nowrap text-muted small">{formatDate(record.updated_at)}</td>
                                    <td className="text-nowrap">{record.language}</td>
                                    <td>
                                        {record.old_value
                                            ? <DiffView base={record.old_value} next={record.new_value} />
                                            : <span className="small">{record.new_value}</span>
                                        }
                                    </td>
                                    <td className="text-nowrap small">{record.editor}</td>
                                    <td className="text-nowrap">
                                        <Badge bg={STATUS_VARIANT[record.status] ?? 'secondary'} text={record.status === 'in_review' ? 'dark' : undefined}>
                                            {record.status.replace('_', ' ')}
                                        </Badge>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                </div>
            ))}
        </Container>
    )
}

export default HistoryPage
