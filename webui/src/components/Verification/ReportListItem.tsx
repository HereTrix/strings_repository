import { FC, useState } from "react"
import { Badge, Button, ListGroup, Spinner, Stack } from "react-bootstrap"
import { ProjectRole } from "../../types/Project"
import { VerificationReport } from "../../types/Verification"
import ConfirmationAlert from "../UI/ConfirmationAlert"

type ReportListItemProps = {
    report: VerificationReport
    projectId: number
    role: ProjectRole
    onDelete: (id: number) => void
    onClick: (id: number) => void
}

const MODE_LABELS: Record<string, string> = {
    source_quality: 'Source Quality',
    translation_accuracy: 'Translation Accuracy',
}

const STATUS_VARIANT: Record<string, string> = {
    pending: 'secondary',
    running: 'warning',
    complete: 'success',
    failed: 'danger',
}

const ReportListItem: FC<ReportListItemProps> = ({ report, role, onDelete, onClick }) => {
    const isAdmin = role === ProjectRole.owner || role === ProjectRole.admin
    const [confirmMessage, setConfirmMessage] = useState<string>()

    return (
        <>
        <ConfirmationAlert
            message={confirmMessage}
            onDismiss={() => setConfirmMessage(undefined)}
            onConfirm={() => { setConfirmMessage(undefined); onDelete(report.id) }}
        />
        <ListGroup.Item
            action
            onClick={() => onClick(report.id)}
            className="py-2"
        >
            <Stack direction="horizontal" gap={2} className="flex-wrap">
                <span className="fw-semibold">
                    {MODE_LABELS[report.mode] ?? report.mode}
                    {report.mode === 'translation_accuracy' && report.target_language && (
                        <span className="text-muted ms-1">→ {report.target_language}</span>
                    )}
                </span>

                <Badge bg={STATUS_VARIANT[report.status] ?? 'secondary'}>
                    {report.status === 'running' && <Spinner size="sm" className="me-1" />}
                    {report.status}
                </Badge>

                {report.status === 'complete' && report.summary && (
                    <Stack direction="horizontal" gap={1}>
                        <Badge bg="success">ok/{report.summary.ok}</Badge>
                        <Badge bg="warning" text="dark">warn/{report.summary.warning}</Badge>
                        <Badge bg="danger">err/{report.summary.error}</Badge>
                    </Stack>
                )}

                {report.is_readonly && <Badge bg="secondary">Read-only</Badge>}

                <span className="text-muted small ms-auto">
                    {new Date(report.created_at).toLocaleDateString()}
                </span>

                {isAdmin && (
                    <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={e => {
                            e.stopPropagation()
                            setConfirmMessage('Delete this verification report? This cannot be undone.')
                        }}
                    >
                        Delete
                    </Button>
                )}
            </Stack>

            {report.status === 'failed' && report.error_message && (
                <div className="text-danger small mt-1">{report.error_message}</div>
            )}
        </ListGroup.Item>
        </>
    )
}

export default ReportListItem
