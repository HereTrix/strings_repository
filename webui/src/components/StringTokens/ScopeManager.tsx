import { FC, JSX, useCallback, useEffect, useRef, useState } from "react"
import { Badge, Button, Col, Form, ListGroup, Modal, Row, Stack } from "react-bootstrap"
import { APIMethod, http, upload } from "../../utils/network"
import Project from "../../types/Project"
import Scope, { ScopeImage } from "../../types/Scope"
import ErrorAlert from "../UI/ErrorAlert"
import ConfirmationAlert from "../UI/ConfirmationAlert"
import ScopeTokenAssigner from "./ScopeTokenAssigner"

type ScopeManagerProps = {
    project: Project
    onHide?: () => void
}

const ScopeManager: FC<ScopeManagerProps> = ({ project, onHide }): JSX.Element => {
    const [scopes, setScopes] = useState<Scope[]>([])
    const [selectedScope, setSelectedScope] = useState<Scope>()
    const [newScopeName, setNewScopeName] = useState('')
    const [description, setDescription] = useState('')
    const [deletionScope, setDeletionScope] = useState<Scope>()
    const [error, setError] = useState<string>()
    const fileInputRef = useRef<HTMLInputElement>(null)
    const selectedScopeIdRef = useRef<number | undefined>(undefined)

    const fetchScopes = useCallback(async () => {
        const result = await http<Scope[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/scopes`,
        })
        if (result.value) {
            setScopes(result.value)
            if (selectedScopeIdRef.current !== undefined) {
                const updated = result.value.find(s => s.id === selectedScopeIdRef.current)
                if (updated) setSelectedScope(updated)
            }
        } else {
            setError(result.error)
        }
    }, [project.id])

    useEffect(() => {
        fetchScopes()
    }, [fetchScopes])

    const selectScope = (scope: Scope) => {
        selectedScopeIdRef.current = scope.id
        setSelectedScope(scope)
        setDescription(scope.description)
    }

    const createScope = async () => {
        if (!newScopeName.trim()) return
        const result = await http<Scope>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/scopes`,
            data: { name: newScopeName.trim(), description: '' },
        })
        if (result.value) {
            setNewScopeName('')
            await fetchScopes()
        } else {
            setError(result.error)
        }
    }

    const confirmDeleteScope = async (scope: Scope) => {
        setDeletionScope(undefined)
        await http({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/scopes/${scope.id}`,
        })
        if (selectedScope?.id === scope.id) {
            setSelectedScope(undefined)
            selectedScopeIdRef.current = undefined
        }
        await fetchScopes()
    }

    const saveDescription = async () => {
        if (!selectedScope) return
        const result = await http<Scope>({
            method: APIMethod.patch,
            path: `/api/project/${project.id}/scopes/${selectedScope.id}`,
            data: { description },
        })
        if (result.error) setError(result.error)
        else await fetchScopes()
    }

    const uploadImage = async (file: File) => {
        if (!selectedScope) return
        const result = await upload<Scope>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/scopes/${selectedScope.id}/image`,
            data: { image: file },
        })
        if (result.error) setError(result.error)
        else await fetchScopes()
    }

    const removeImage = async (img: ScopeImage) => {
        if (!selectedScope) return
        const result = await http({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/scopes/${selectedScope.id}/image`,
            data: { image_id: img.id },
        })
        if (result.error) setError(result.error)
        else await fetchScopes()
    }

    const body = (
        <Row style={{ minHeight: onHide ? '460px' : '500px' }}>
            <Col md={3} className="border-end">
                <ListGroup variant="flush">
                    {scopes.map(scope => (
                        <ListGroup.Item
                            key={scope.id}
                            action
                            active={selectedScope?.id === scope.id}
                            onClick={() => selectScope(scope)}
                            className="d-flex justify-content-between align-items-center"
                        >
                            <Stack direction="horizontal" gap={2} className="overflow-hidden">
                                {scope.images[0] && (
                                    <img
                                        src={scope.images[0].url}
                                        alt={scope.name}
                                        width={24}
                                        height={24}
                                        style={{ objectFit: 'cover', borderRadius: 4, flexShrink: 0 }}
                                    />
                                )}
                                <span className="text-truncate">{scope.name}</span>
                            </Stack>
                            <Badge bg="secondary" className="ms-2 flex-shrink-0">{scope.token_count}</Badge>
                        </ListGroup.Item>
                    ))}
                </ListGroup>
                <div className="p-2 border-top mt-2">
                    <Stack direction="horizontal" gap={2}>
                        <Form.Control
                            size="sm"
                            placeholder="New scope name"
                            value={newScopeName}
                            onChange={e => setNewScopeName(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') createScope() }}
                        />
                        <Button size="sm" onClick={createScope} disabled={!newScopeName.trim()}>Add</Button>
                    </Stack>
                </div>
            </Col>

            <Col md={9}>
                {!selectedScope ? (
                    <p className="text-muted mt-3">Select a scope to edit it.</p>
                ) : (
                    <Stack gap={onHide ? 3 : 4} className={onHide ? 'p-1' : 'p-2'}>
                        <div className="d-flex justify-content-between align-items-start">
                            {onHide
                                ? <h6 className="mb-0">{selectedScope.name}</h6>
                                : <h5 className="mb-0">{selectedScope.name}</h5>
                            }
                            <Button
                                size="sm"
                                variant="outline-danger"
                                onClick={() => setDeletionScope(selectedScope)}
                            >
                                Delete scope
                            </Button>
                        </div>

                        <Row className={onHide ? 'g-2' : 'g-3'}>
                            <Col md={6}>
                                <Form.Group>
                                    <Form.Label className="small fw-semibold">Description</Form.Label>
                                    <Form.Control
                                        as="textarea"
                                        rows={onHide ? 2 : 3}
                                        value={description}
                                        onChange={e => setDescription(e.target.value)}
                                    />
                                    <Button size="sm" className="mt-1" onClick={saveDescription}>
                                        Save description
                                    </Button>
                                </Form.Group>
                            </Col>
                            <Col md={6}>
                                <Form.Label className="small fw-semibold d-block">
                                    Screenshots ({selectedScope.images.length})
                                </Form.Label>
                                <div className="d-flex flex-wrap gap-2 mb-2">
                                    {selectedScope.images.map(img => (
                                        <div key={img.id} style={{ position: 'relative', display: 'inline-block' }}>
                                            <img
                                                src={img.url}
                                                alt=""
                                                width={onHide ? 64 : 80}
                                                height={onHide ? 48 : 60}
                                                style={{ objectFit: 'cover', borderRadius: 4, display: 'block' }}
                                            />
                                            <Button
                                                size="sm"
                                                variant="danger"
                                                style={{
                                                    position: 'absolute',
                                                    top: 2,
                                                    right: 2,
                                                    padding: '0 4px',
                                                    lineHeight: 1.2,
                                                    fontSize: '0.7rem',
                                                }}
                                                onClick={() => removeImage(img)}
                                            >
                                                ×
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*"
                                    className="d-none"
                                    onChange={e => {
                                        const file = e.target.files?.[0]
                                        if (file) uploadImage(file)
                                        e.target.value = ''
                                    }}
                                />
                                <Button
                                    size="sm"
                                    variant="outline-secondary"
                                    onClick={() => fileInputRef.current?.click()}
                                >
                                    + Add screenshot
                                </Button>
                            </Col>
                        </Row>

                        <div>
                            <Form.Label className="small fw-semibold">Localization keys</Form.Label>
                            <ScopeTokenAssigner
                                projectId={project.id}
                                scope={selectedScope}
                                onUpdate={fetchScopes}
                            />
                        </div>
                    </Stack>
                )}
            </Col>
        </Row>
    )

    return (
        <>
            {onHide ? (
                <Modal show onHide={onHide} size="xl">
                    <Modal.Header closeButton>
                        <Modal.Title>Manage Scopes</Modal.Title>
                    </Modal.Header>
                    <Modal.Body>{body}</Modal.Body>
                </Modal>
            ) : (
                <div className="mt-3">{body}</div>
            )}

            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
            {deletionScope && (
                <ConfirmationAlert
                    message={`Delete scope "${deletionScope.name}"? This will not delete the keys.`}
                    onDismiss={() => setDeletionScope(undefined)}
                    onConfirm={() => confirmDeleteScope(deletionScope)}
                />
            )}
        </>
    )
}

export default ScopeManager
