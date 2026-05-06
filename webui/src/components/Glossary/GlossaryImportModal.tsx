import { FC, useState } from "react"
import { Alert, Button, Form, Modal, Spinner } from "react-bootstrap"
import Project from "../../types/Project"
import { GlossaryImportResult } from "../../types/Glossary"
import { APIMethod, upload } from "../../utils/network"

interface GlossaryImportModalProps {
  project: Project
  show: boolean
  onHide: () => void
  onImported: () => void
}

const GlossaryImportModal: FC<GlossaryImportModalProps> = ({ project, show, onHide, onImported }) => {
  const [file, setFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState<GlossaryImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleImport = async () => {
    if (!file) return
    setImporting(true)
    setError(null)

    const response = await upload<GlossaryImportResult>({
      method: APIMethod.post,
      path: `/api/project/${project.id}/glossary/import`,
      data: { file },
    })

    setImporting(false)

    if (response.value) {
      setResult(response.value)
    } else {
      setError(response.error ?? 'Import failed.')
    }
  }

  const handleClose = () => {
    if (result) onImported()
    onHide()
    setFile(null)
    setResult(null)
    setError(null)
  }

  return (
    <Modal show={show} onHide={handleClose}>
      <Modal.Header closeButton>
        <Modal.Title>Import Glossary (CSV)</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {error && <Alert variant="danger">{error}</Alert>}
        {result ? (
          <>
            <Alert variant="success">
              Imported: {result.imported}, Updated: {result.updated}, Skipped: {result.skipped}
            </Alert>
            {result.warnings.length > 0 && (
              <Alert variant="warning">
                <ul className="mb-0">
                  {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </Alert>
            )}
          </>
        ) : (
          <>
            <Form.Group className="mb-3">
              <Form.Control
                type="file"
                accept=".csv"
                onChange={e => setFile((e.target as HTMLInputElement).files?.[0] ?? null)}
              />
            </Form.Group>
            <p className="text-muted small">
              Expected columns: term, definition, case_sensitive, language_code, preferred_translation. Multiple rows per term for multiple languages.
            </p>
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        {!result && (
          <Button onClick={handleImport} disabled={!file || importing}>
            {importing ? <><Spinner size="sm" className="me-1" />Importing…</> : 'Import'}
          </Button>
        )}
        <Button variant="secondary" onClick={handleClose}>Close</Button>
      </Modal.Footer>
    </Modal>
  )
}

export default GlossaryImportModal
