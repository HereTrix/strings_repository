import { FC, JSX, useEffect, useState } from "react"
import { Badge, Button, Container, ListGroup, Modal, Spinner, Stack } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import { Bundle } from "../model/Bundle"
import Project, { ProjectRole } from "../model/Project"
import BundleCompareModal from "./BundleCompareModal"
import BundleExportModal from "./BundleExportModal"
import CreateBundleModal from "./CreateBundleModal"

type BundlesPageProps = {
    project: Project
}

const canCreate = (role: ProjectRole) =>
    role === ProjectRole.owner || role === ProjectRole.admin || role === ProjectRole.editor

const canManage = (role: ProjectRole) =>
    role === ProjectRole.owner || role === ProjectRole.admin

const BundlesPage: FC<BundlesPageProps> = ({ project }): JSX.Element => {
    const [bundles, setBundles] = useState<Bundle[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | undefined>()

    const [showCreate, setShowCreate] = useState(false)
    const [compareBundle, setCompareBundle] = useState<Bundle | undefined>()
    const [exportBundle, setExportBundle] = useState<Bundle | undefined>()
    const [deleteCandidate, setDeleteCandidate] = useState<Bundle | undefined>()

    const loadBundles = async () => {
        setLoading(true)
        const result = await http<Bundle[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/bundles`,
        })
        setLoading(false)
        if (result.value) {
            setBundles(result.value)
        } else {
            setError(result.error)
        }
    }

    useEffect(() => {
        loadBundles()
    }, [project.id])

    const activate = async (bundle: Bundle) => {
        const result = await http<Bundle>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/bundles/${bundle.id}/activate`,
        })
        if (result.value) {
            setBundles(prev => prev.map(b => ({ ...b, is_active: b.id === bundle.id })))
        } else {
            setError(result.error)
        }
    }

    const deactivate = async (bundle: Bundle) => {
        const result = await http<Bundle>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/bundles/${bundle.id}/deactivate`,
        })
        if (result.value) {
            setBundles(prev => prev.map(b => b.id === bundle.id ? { ...b, is_active: false } : b))
        } else {
            setError(result.error)
        }
    }

    const deleteBundle = async (bundle: Bundle) => {
        const result = await http<void>({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/bundles/${bundle.id}`,
        })
        if (!result.error) {
            setBundles(prev => prev.filter(b => b.id !== bundle.id))
        } else {
            setError(result.error)
        }
    }

    const formatDate = (iso: string) =>
        new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })

    return (
        <Container className="mt-3">
            <Stack direction="horizontal" className="mb-3">
                <h5 className="mb-0">Bundles</h5>
                {canCreate(project.role) && (
                    <Button className="ms-auto" size="sm" onClick={() => setShowCreate(true)}>
                        Create bundle
                    </Button>
                )}
            </Stack>

            {error && <p className="text-danger">{error}</p>}

            {loading && (
                <Stack direction="horizontal" gap={2} className="justify-content-center py-4">
                    <Spinner size="sm" />
                    <span>Loading…</span>
                </Stack>
            )}

            {!loading && bundles.length === 0 && (
                <p className="text-muted text-center py-4">
                    No bundles yet.{canCreate(project.role) ? " Create the first one to snapshot the current translations." : ""}
                </p>
            )}

            <ListGroup>
                {bundles.map(bundle => (
                    <ListGroup.Item key={bundle.id}>
                        <Stack direction="horizontal" gap={2} className="flex-wrap">
                            <Stack gap={0}>
                                <Stack direction="horizontal" gap={2}>
                                    <strong>{bundle.version_name}</strong>
                                    {bundle.is_active && <Badge bg="success">active</Badge>}
                                </Stack>
                                <small className="text-muted">
                                    {bundle.translation_count} translations
                                    {" · "}
                                    {formatDate(bundle.created_at)}
                                    {bundle.created_by && ` · ${bundle.created_by}`}
                                </small>
                            </Stack>

                            <Stack direction="horizontal" gap={2} className="ms-auto flex-wrap">
                                <Button
                                    variant="outline-secondary"
                                    size="sm"
                                    onClick={() => setCompareBundle(bundle)}
                                >
                                    Compare
                                </Button>
                                <Button
                                    variant="outline-secondary"
                                    size="sm"
                                    onClick={() => setExportBundle(bundle)}
                                >
                                    Export
                                </Button>
                                {canManage(project.role) && (
                                    <>
                                        {bundle.is_active ? (
                                            <Button
                                                variant="outline-warning"
                                                size="sm"
                                                onClick={() => deactivate(bundle)}
                                            >
                                                Deactivate
                                            </Button>
                                        ) : (
                                            <Button
                                                variant="outline-success"
                                                size="sm"
                                                onClick={() => activate(bundle)}
                                            >
                                                Activate
                                            </Button>
                                        )}
                                        <Button
                                            variant="outline-danger"
                                            size="sm"
                                            disabled={bundle.is_active}
                                            title={bundle.is_active ? "Deactivate before deleting" : undefined}
                                            onClick={() => setDeleteCandidate(bundle)}
                                        >
                                            Delete
                                        </Button>
                                    </>
                                )}
                            </Stack>
                        </Stack>
                    </ListGroup.Item>
                ))}
            </ListGroup>

            {showCreate && (
                <CreateBundleModal
                    project={project}
                    show={showCreate}
                    onHide={() => setShowCreate(false)}
                    onCreated={(bundle) => {
                        setBundles(prev => [bundle, ...prev])
                        setShowCreate(false)
                    }}
                />
            )}

            {compareBundle && (
                <BundleCompareModal
                    project={project}
                    bundles={bundles}
                    initialFrom={compareBundle}
                    show={!!compareBundle}
                    onHide={() => setCompareBundle(undefined)}
                />
            )}

            {exportBundle && (
                <BundleExportModal
                    project={project}
                    bundle={exportBundle}
                    show={!!exportBundle}
                    onHide={() => setExportBundle(undefined)}
                />
            )}

            <Modal show={!!deleteCandidate} onHide={() => setDeleteCandidate(undefined)} centered>
                <Modal.Header closeButton>
                    <Modal.Title>Delete bundle</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    Are you sure you want to delete bundle <strong>{deleteCandidate?.version_name}</strong>? This action cannot be undone.
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setDeleteCandidate(undefined)}>Cancel</Button>
                    <Button
                        variant="danger"
                        onClick={() => {
                            if (deleteCandidate) deleteBundle(deleteCandidate)
                            setDeleteCandidate(undefined)
                        }}
                    >
                        Delete
                    </Button>
                </Modal.Footer>
            </Modal>
        </Container>
    )
}

export default BundlesPage
