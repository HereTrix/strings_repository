import fileDownload from "js-file-download"
import { FC, JSX, useEffect, useState } from "react"
import { Badge, Button, Dropdown, DropdownButton, ListGroup, Modal, Spinner, Stack } from "react-bootstrap"
import { APIMethod, download, http } from "../../utils/network"
import { Bundle, BundleDiff } from "../../types/Bundle"
import DiffView from "../UI/DiffView"
import Project from "../../types/Project"

type BundleCompareModalProps = {
    project: Project
    bundles: Bundle[]
    initialFrom: Bundle
    show: boolean
    onHide: () => void
}

type CompareSource = Bundle | 'live'

const sourceName = (s: CompareSource) => s === 'live' ? 'Live translations' : s.version_name

const BundleCompareModal: FC<BundleCompareModalProps> = ({ project, bundles, initialFrom, show, onHide }): JSX.Element => {
    const [fromSource, setFromSource] = useState<CompareSource>(initialFrom)
    const [toSource, setToSource] = useState<CompareSource>('live')
    const [diff, setDiff] = useState<BundleDiff | undefined>()
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | undefined>()
    const [expandChanged, setExpandChanged] = useState(true)
    const [expandAdded, setExpandAdded] = useState(false)
    const [expandRemoved, setExpandRemoved] = useState(false)
    const [expandNewTokens, setExpandNewTokens] = useState(true)
    const [expandDeletedTokens, setExpandDeletedTokens] = useState(false)

    const sourceId = (s: CompareSource) => s === 'live' ? 'live' : String(s.id)

    const compare = async () => {
        setLoading(true)
        setError(undefined)
        setDiff(undefined)

        const result = await http<BundleDiff>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/bundles/compare`,
            params: { from: sourceId(fromSource), to: sourceId(toSource) },
        })

        setLoading(false)

        if (result.value) {
            setDiff(result.value)
        } else {
            setError(result.error)
        }
    }

    useEffect(() => {
        if (show) compare()
    }, [show, fromSource, toSource])

    const exportCompare = async (mode: 'diff' | 'changes') => {
        const result = await download({
            method: APIMethod.get,
            path: `/api/project/${project.id}/bundles/compare/export`,
            params: { from: sourceId(fromSource), to: sourceId(toSource), mode },
        })
        if (result.value) {
            fileDownload(result.value.content, result.value.name || `compare_${mode}.xlsx`)
        }
    }

    const otherBundles = bundles.filter(b => b.id !== (fromSource !== 'live' ? fromSource.id : -1))

    return (
        <Modal show={show} onHide={onHide} size="lg" scrollable>
            <Modal.Header closeButton>
                <Modal.Title>Compare bundles</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Stack direction="horizontal" gap={2} className="mb-3 flex-wrap">
                    <span className="text-muted">From</span>
                    <DropdownButton title={sourceName(fromSource)} variant="outline-secondary" size="sm">
                        {bundles.map(b => (
                            <Dropdown.Item key={b.id} onClick={() => setFromSource(b)}>
                                {b.version_name}
                                {b.is_active && <Badge bg="success" className="ms-2">active</Badge>}
                            </Dropdown.Item>
                        ))}
                        <Dropdown.Item onClick={() => setFromSource('live')}>Live translations</Dropdown.Item>
                    </DropdownButton>
                    <span className="text-muted">→</span>
                    <DropdownButton title={sourceName(toSource)} variant="outline-secondary" size="sm">
                        {otherBundles.map(b => (
                            <Dropdown.Item key={b.id} onClick={() => setToSource(b)}>
                                {b.version_name}
                                {b.is_active && <Badge bg="success" className="ms-2">active</Badge>}
                            </Dropdown.Item>
                        ))}
                        <Dropdown.Item onClick={() => setToSource('live')}>Live translations</Dropdown.Item>
                    </DropdownButton>
                </Stack>

                {loading && (
                    <Stack direction="horizontal" gap={2} className="justify-content-center py-4">
                        <Spinner size="sm" />
                        <span>Comparing…</span>
                    </Stack>
                )}

                {error && <p className="text-danger">{error}</p>}

                {diff && !loading && (
                    <>
                        <Stack direction="horizontal" gap={3} className="mb-3 flex-wrap">
                            {diff.new_tokens.length > 0 && <Badge bg="info">{diff.new_tokens.length} new key{diff.new_tokens.length !== 1 ? 's' : ''}</Badge>}
                            {diff.deleted_tokens.length > 0 && <Badge bg="dark">{diff.deleted_tokens.length} deleted key{diff.deleted_tokens.length !== 1 ? 's' : ''}</Badge>}
                            <Badge bg="success">{diff.added.length} added</Badge>
                            <Badge bg="danger">{diff.removed.length} removed</Badge>
                            <Badge bg="warning" text="dark">{diff.changed.length} changed</Badge>
                            <span className="text-muted small">{diff.unchanged_count} unchanged</span>
                        </Stack>

                        {diff.changed.length > 0 && (
                            <>
                                <Button
                                    variant="link"
                                    className="p-0 mb-1 text-decoration-none"
                                    onClick={() => setExpandChanged(v => !v)}
                                >
                                    {expandChanged ? "▾" : "▸"} Changed ({diff.changed.length})
                                </Button>
                                {expandChanged && (
                                    <ListGroup className="mb-3">
                                        {diff.changed.map((entry, i) => (
                                            <ListGroup.Item key={i}>
                                                <Stack direction="horizontal" gap={2} className="mb-1">
                                                    <code className="small">{entry.token}</code>
                                                    <Badge bg="secondary" className="ms-auto">{entry.language}</Badge>
                                                </Stack>
                                                <DiffView base={entry.from!} next={entry.to!} />
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                )}
                            </>
                        )}

                        {diff.added.length > 0 && (
                            <>
                                <Button
                                    variant="link"
                                    className="p-0 mb-1 text-decoration-none text-success"
                                    onClick={() => setExpandAdded(v => !v)}
                                >
                                    {expandAdded ? "▾" : "▸"} Added ({diff.added.length})
                                </Button>
                                {expandAdded && (
                                    <ListGroup className="mb-3">
                                        {diff.added.map((entry, i) => (
                                            <ListGroup.Item key={i} variant="success">
                                                <Stack direction="horizontal" gap={2}>
                                                    <code className="small">{entry.token}</code>
                                                    <Badge bg="secondary" className="ms-auto">{entry.language}</Badge>
                                                    <span className="small">{entry.value}</span>
                                                </Stack>
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                )}
                            </>
                        )}

                        {diff.removed.length > 0 && (
                            <>
                                <Button
                                    variant="link"
                                    className="p-0 mb-1 text-decoration-none text-danger"
                                    onClick={() => setExpandRemoved(v => !v)}
                                >
                                    {expandRemoved ? "▾" : "▸"} Removed ({diff.removed.length})
                                </Button>
                                {expandRemoved && (
                                    <ListGroup className="mb-3">
                                        {diff.removed.map((entry, i) => (
                                            <ListGroup.Item key={i} variant="danger">
                                                <Stack direction="horizontal" gap={2}>
                                                    <code className="small">{entry.token}</code>
                                                    <Badge bg="secondary" className="ms-auto">{entry.language}</Badge>
                                                </Stack>
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                )}
                            </>
                        )}

                        {diff.new_tokens.length > 0 && (
                            <>
                                <Button
                                    variant="link"
                                    className="p-0 mb-1 text-decoration-none text-info"
                                    onClick={() => setExpandNewTokens(v => !v)}
                                >
                                    {expandNewTokens ? "▾" : "▸"} New keys — not yet translated ({diff.new_tokens.length})
                                </Button>
                                {expandNewTokens && (
                                    <ListGroup className="mb-3">
                                        {diff.new_tokens.map((token, i) => (
                                            <ListGroup.Item key={i} variant="info">
                                                <code className="small">{token}</code>
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                )}
                            </>
                        )}

                        {diff.deleted_tokens.length > 0 && (
                            <>
                                <Button
                                    variant="link"
                                    className="p-0 mb-1 text-decoration-none text-secondary"
                                    onClick={() => setExpandDeletedTokens(v => !v)}
                                >
                                    {expandDeletedTokens ? "▾" : "▸"} Deleted keys ({diff.deleted_tokens.length})
                                </Button>
                                {expandDeletedTokens && (
                                    <ListGroup className="mb-3">
                                        {diff.deleted_tokens.map((token, i) => (
                                            <ListGroup.Item key={i} variant="secondary">
                                                <code className="small">{token}</code>
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                )}
                            </>
                        )}

                        {diff.added.length === 0 && diff.removed.length === 0 && diff.changed.length === 0
                            && diff.new_tokens.length === 0 && diff.deleted_tokens.length === 0 && (
                            <p className="text-muted text-center py-3">No differences found.</p>
                        )}
                    </>
                )}
            </Modal.Body>
            <Modal.Footer>
                <Stack direction="horizontal" gap={2} className="me-auto">
                    <Button
                        variant="outline-secondary"
                        size="sm"
                        disabled={!diff || loading}
                        onClick={() => exportCompare('diff')}
                    >
                        Export diff
                    </Button>
                    <Button
                        variant="outline-secondary"
                        size="sm"
                        disabled={!diff || loading}
                        onClick={() => exportCompare('changes')}
                    >
                        Export changes
                    </Button>
                </Stack>
                <Button variant="secondary" onClick={onHide}>Close</Button>
            </Modal.Footer>
        </Modal>
    )
}

export default BundleCompareModal
