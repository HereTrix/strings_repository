import { FC, useEffect, useState } from "react"
import { Alert, Button, Container, Spinner, Stack, Table } from "react-bootstrap"
import Project, { ProjectRole } from "../../types/Project"
import { GlossaryExtractionJob, GlossarySuggestion, GlossaryTerm } from "../../types/Glossary"
import { APIMethod, http } from "../../utils/network"
import GlossaryTermModal from "./GlossaryTermModal"
import GlossaryTermRow from "./GlossaryTermRow"
import GlossarySuggestionsPanel from "./GlossarySuggestionsPanel"
import GlossaryImportModal from "./GlossaryImportModal"
import ConfirmationAlert from "../UI/ConfirmationAlert"

interface GlossaryPageProps {
  project: Project
}

const GlossaryPage: FC<GlossaryPageProps> = ({ project }) => {
  const [terms, setTerms] = useState<GlossaryTerm[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingTerm, setEditingTerm] = useState<GlossaryTerm | undefined>()
  const [showAddModal, setShowAddModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [deletingTerm, setDeletingTerm] = useState<GlossaryTerm | undefined>()
  const [extractionJob, setExtractionJob] = useState<GlossaryExtractionJob | null>(null)
  const [suggestions, setSuggestions] = useState<GlossarySuggestion[]>([])

  const canManage = project.role === ProjectRole.owner || project.role === ProjectRole.admin

  const fetchTerms = async () => {
    const result = await http<GlossaryTerm[]>({
      method: APIMethod.get,
      path: `/api/project/${project.id}/glossary`,
    })
    setLoading(false)
    if (result.value) setTerms(result.value)
    else setError(result.error ?? 'Failed to load glossary.')
  }

  const fetchExtractionJob = async () => {
    const result = await http<GlossaryExtractionJob>({
      method: APIMethod.get,
      path: `/api/project/${project.id}/glossary/extract`,
    })
    if (result.value) {
      setExtractionJob(result.value)
      if (result.value.status === 'complete') {
        fetchSuggestions()
      }
    } else {
      setExtractionJob(null)
    }
  }

  const fetchSuggestions = async () => {
    const result = await http<GlossarySuggestion[]>({
      method: APIMethod.get,
      path: `/api/project/${project.id}/glossary/suggestions`,
    })
    if (result.value) setSuggestions(result.value)
  }

  useEffect(() => {
    fetchTerms()
    if (project.has_ai_provider) fetchExtractionJob()
  }, [])

  useEffect(() => {
    if (extractionJob?.status !== 'pending' && extractionJob?.status !== 'running') return
    const timer = setInterval(async () => {
      const result = await http<GlossaryExtractionJob>({
        method: APIMethod.get,
        path: `/api/project/${project.id}/glossary/extract`,
      })
      if (result.value) {
        setExtractionJob(result.value)
        if (result.value.status === 'complete') {
          fetchSuggestions()
        }
      }
    }, 5000)
    return () => clearInterval(timer)
  }, [extractionJob?.status])

  const handleExport = () => {
    window.open(`/api/project/${project.id}/glossary/export`, '_blank')
  }

  const handleTriggerExtraction = async () => {
    const result = await http<GlossaryExtractionJob>({
      method: APIMethod.post,
      path: `/api/project/${project.id}/glossary/extract`,
    })
    if (result.value) setExtractionJob(result.value)
    else setError(result.error ?? 'Failed to start extraction.')
  }

  const handleDeleteConfirm = async () => {
    if (!deletingTerm) return
    await http({
      method: APIMethod.delete,
      path: `/api/project/${project.id}/glossary/${deletingTerm.id}`,
    })
    setDeletingTerm(undefined)
    fetchTerms()
  }

  const handleTermSaved = (saved: GlossaryTerm) => {
    setTerms(prev => {
      const idx = prev.findIndex(t => t.id === saved.id)
      if (idx >= 0) {
        const next = [...prev]
        next[idx] = saved
        return next
      }
      return [...prev, saved]
    })
  }

  const isExtracting = extractionJob?.status === 'pending' || extractionJob?.status === 'running'

  return (
    <Container className="py-3">
      {error && <Alert variant="danger">{error}</Alert>}
      <Stack direction="horizontal" gap={2} className="mb-3">
        <h4 className="mb-0">Glossary</h4>
        {canManage && (
          <Button size="sm" onClick={() => setShowAddModal(true)}>Add Term</Button>
        )}
        {canManage && (
          <Button size="sm" variant="outline-secondary" onClick={() => setShowImportModal(true)}>Import CSV</Button>
        )}
        <Button size="sm" variant="outline-secondary" onClick={handleExport}>Export CSV</Button>
        {project.has_ai_provider && canManage && (
          <Button
            size="sm"
            variant="outline-info"
            onClick={handleTriggerExtraction}
            disabled={isExtracting}
          >
            {isExtracting ? <><Spinner size="sm" className="me-1" />Extracting…</> : 'Extract with AI'}
          </Button>
        )}
      </Stack>

      {extractionJob?.status === 'failed' && (
        <Alert variant="danger">Extraction failed: {extractionJob.error_message}</Alert>
      )}

      {loading ? (
        <Spinner size="sm" />
      ) : (
        <>
          <Table responsive>
            <thead>
              <tr>
                <th>Term</th>
                <th>Definition</th>
                <th>Languages</th>
                {canManage && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {terms.map(t => (
                <GlossaryTermRow
                  key={t.id}
                  term={t}
                  canManage={canManage}
                  onEdit={setEditingTerm}
                  onDelete={setDeletingTerm}
                />
              ))}
            </tbody>
          </Table>
          {terms.length === 0 && <p className="text-muted">No glossary terms yet.</p>}
        </>
      )}

      {suggestions.length > 0 && (
        <GlossarySuggestionsPanel
          project={project}
          suggestions={suggestions}
          onAccepted={fetchTerms}
        />
      )}

      <ConfirmationAlert
        message={deletingTerm ? `Delete term "${deletingTerm.term}"? This cannot be undone.` : undefined}
        onConfirm={handleDeleteConfirm}
        onDismiss={() => setDeletingTerm(undefined)}
      />

      <GlossaryTermModal
        show={showAddModal}
        project={project}
        onHide={() => setShowAddModal(false)}
        onSaved={handleTermSaved}
      />
      {editingTerm && (
        <GlossaryTermModal
          show={true}
          project={project}
          term={editingTerm}
          onHide={() => setEditingTerm(undefined)}
          onSaved={handleTermSaved}
        />
      )}
      {showImportModal && (
        <GlossaryImportModal
          project={project}
          show={showImportModal}
          onHide={() => setShowImportModal(false)}
          onImported={() => { fetchTerms(); setShowImportModal(false) }}
        />
      )}
    </Container>
  )
}

export default GlossaryPage
