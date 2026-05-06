import { FC, useEffect, useState } from "react"
import { Alert, Button, Form, Modal, Spinner } from "react-bootstrap"
import Project from "../../types/Project"
import { GlossaryTerm } from "../../types/Glossary"
import { APIMethod, http } from "../../utils/network"

interface GlossaryTermModalProps {
  project: Project
  term?: GlossaryTerm
  show: boolean
  onHide: () => void
  onSaved: (term: GlossaryTerm) => void
}

const GlossaryTermModal: FC<GlossaryTermModalProps> = ({ project, term, show, onHide, onSaved }) => {
  const [termValue, setTermValue] = useState('')
  const [definition, setDefinition] = useState('')
  const [caseSensitive, setCaseSensitive] = useState(false)
  const [translations, setTranslations] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (show) {
      setTermValue(term?.term ?? '')
      setDefinition(term?.definition ?? '')
      setCaseSensitive(term?.case_sensitive ?? false)
      const initTranslations: Record<string, string> = {}
      if (term) {
        for (const tr of term.translations) {
          initTranslations[tr.language_code] = tr.preferred_translation
        }
      }
      setTranslations(initTranslations)
      setError(null)
    }
  }, [show])

  const handleSubmit = async () => {
    setSaving(true)
    setError(null)

    const body = {
      term: termValue.trim(),
      definition,
      case_sensitive: caseSensitive,
      translations: Object.entries(translations)
        .filter(([, v]) => v.trim())
        .map(([language_code, preferred_translation]) => ({ language_code, preferred_translation })),
    }

    const path = term
      ? `/api/project/${project.id}/glossary/${term.id}`
      : `/api/project/${project.id}/glossary`

    const result = await http<GlossaryTerm>({
      method: term ? APIMethod.put : APIMethod.post,
      path,
      data: body,
    })

    setSaving(false)

    if (result.value) {
      onSaved(result.value)
      onHide()
    } else if (result.error?.includes('already exists') || result.error?.includes('409')) {
      setError('A term with this name already exists.')
    } else {
      setError(result.error ?? 'Failed to save term.')
    }
  }

  return (
    <Modal show={show} onHide={onHide}>
      <Modal.Header closeButton>
        <Modal.Title>{term ? 'Edit Glossary Term' : 'Add Glossary Term'}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {error && <Alert variant="danger">{error}</Alert>}
        <Form>
          <Form.Group className="mb-3">
            <Form.Label>Term <span className="text-danger">*</span></Form.Label>
            <Form.Control
              type="text"
              value={termValue}
              maxLength={500}
              onChange={e => setTermValue(e.target.value)}
            />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>Definition</Form.Label>
            <Form.Control
              as="textarea"
              rows={3}
              value={definition}
              onChange={e => setDefinition(e.target.value)}
            />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Check
              label="Case-sensitive"
              checked={caseSensitive}
              onChange={e => setCaseSensitive(e.target.checked)}
            />
          </Form.Group>
          {project.languages.map(lang => (
            <Form.Group key={lang.code} className="mb-2">
              <Form.Label>Preferred translation [{lang.code}]</Form.Label>
              <Form.Control
                type="text"
                value={translations[lang.code] ?? ''}
                onChange={e => setTranslations(prev => ({ ...prev, [lang.code]: e.target.value }))}
              />
            </Form.Group>
          ))}
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>Cancel</Button>
        <Button onClick={handleSubmit} disabled={saving || !termValue.trim()}>
          {saving ? <><Spinner size="sm" className="me-1" />Saving…</> : 'Save'}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}

export default GlossaryTermModal
