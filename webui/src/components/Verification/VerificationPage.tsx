import React, { FC, Suspense, useEffect, useRef, useState } from "react"
import { Button, ListGroup, Spinner, Stack } from "react-bootstrap"
import Project, { ProjectRole } from "../../types/Project"
import { VerificationReport } from "../../types/Verification"
import { APIMethod, http } from "../../utils/network"
import ReportListItem from "./ReportListItem"
import ErrorAlert from "../UI/ErrorAlert"

const RunVerificationModal = React.lazy(() => import('./RunVerificationModal'))
const ReportDetail = React.lazy(() => import('./ReportDetail'))

type VerificationPageProps = {
    project: Project
}

const VerificationPage: FC<VerificationPageProps> = ({ project }) => {
    const isAdmin = project.role === ProjectRole.owner || project.role === ProjectRole.admin

    const [reports, setReports] = useState<VerificationReport[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string>()
    const [showRunModal, setShowRunModal] = useState(false)
    const [selectedReportId, setSelectedReportId] = useState<number | null>(null)
    const pollTimer = useRef<number | null>(null)

    const loadReports = async () => {
        const result = await http<VerificationReport[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/verify`,
        })
        if (result.value) {
            setReports(result.value)
            return result.value
        } else {
            setError(result.error)
            return []
        }
    }

    const startPolling = (currentReports: VerificationReport[]) => {
        if (pollTimer.current) return
        const hasActive = currentReports.some(r => r.status === 'pending' || r.status === 'running')
        if (!hasActive) return
        pollTimer.current = window.setInterval(async () => {
            const updated = await loadReports()
            const stillActive = updated.some(r => r.status === 'pending' || r.status === 'running')
            if (!stillActive && pollTimer.current) {
                clearInterval(pollTimer.current)
                pollTimer.current = null
            }
        }, 5000)
    }

    useEffect(() => {
        setLoading(true)
        loadReports().then(r => {
            setLoading(false)
            startPolling(r)
        })
        return () => {
            if (pollTimer.current) {
                clearInterval(pollTimer.current)
                pollTimer.current = null
            }
        }
    }, [])

    const handleDelete = async (id: number) => {
        await http({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/verify/${id}`,
        })
        setReports(prev => prev.filter(r => r.id !== id))
    }

    if (selectedReportId !== null) {
        return (
            <Suspense fallback={<Spinner />}>
                <ReportDetail
                    reportId={selectedReportId}
                    project={project}
                    onBack={() => setSelectedReportId(null)}
                    onReportUpdated={() => loadReports()}
                />
            </Suspense>
        )
    }

    return (
        <div className="mt-3">
            <Stack direction="horizontal" gap={3} className="mb-3">
                <h5 className="mb-0">AI Verification</h5>
                {isAdmin && (
                    <Button size="sm" className="ms-auto" onClick={() => setShowRunModal(true)}>
                        Run Verification
                    </Button>
                )}
            </Stack>

            {loading && <Spinner size="sm" />}

            {!loading && reports.length === 0 && (
                <p className="text-muted">No verification reports yet.</p>
            )}

            <ListGroup>
                {reports.map(report => (
                    <ReportListItem
                        key={report.id}
                        report={report}
                        projectId={project.id}
                        role={project.role}
                        onDelete={handleDelete}
                        onClick={id => setSelectedReportId(id)}
                    />
                ))}
            </ListGroup>

            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}

            {showRunModal && (
                <Suspense fallback={null}>
                    <RunVerificationModal
                        show={showRunModal}
                        project={project}
                        onHide={() => setShowRunModal(false)}
                        onSuccess={report => {
                            setReports(prev => [report, ...prev])
                            setShowRunModal(false)
                            startPolling([report, ...reports])
                        }}
                    />
                </Suspense>
            )}
        </div>
    )
}

export default VerificationPage
