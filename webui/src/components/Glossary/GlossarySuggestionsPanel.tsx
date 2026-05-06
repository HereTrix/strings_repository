import { FC, useState } from "react"
import { Alert, Badge, Button, Card, Form, Stack, Table } from "react-bootstrap"
import Project from "../../types/Project"
import { GlossarySuggestion } from "../../types/Glossary"
import { APIMethod, http } from "../../utils/network"

interface GlossarySuggestionsPanelProps {
  project: Project
  suggestions: GlossarySuggestion[]
  onAccepted: () => void
}

interface SuggestionState {
  editMode: boolean
  editedTerm: string
  editedDefinition: string
  editedTranslations: Record<string, string>
  acting: boolean
  error: string | null
}

const GlossarySuggestionsPanel: FC<GlossarySuggestionsPanelProps> = ({ project, suggestions: initialSuggestions, onAccepted }) => {
  const [suggestions, setSuggestions] = useState(initialSuggestions)
  const [states, setStates] = useState<Record<number, SuggestionState>>(() =>
    Object.fromEntries(initialSuggestions.map((s, i) => [i, {
      editMode: false,
      editedTerm: s.term,
      editedDefinition: s.definition,
      editedTranslations: Object.fromEntries(s.translations.map(t => [t.language_code, t.preferred_translation])),
      acting: false,
      error: null,
    }]))
  )

  const pendingCount = suggestions.filter(s => s.status === 'pending').length

  const updateState = (index: number, update: Partial<SuggestionState>) => {
    setStates(prev => ({ ...prev, [index]: { ...prev[index], ...update } }))
  }

  const handleAction = async (index: number, action: 'accept' | 'reject') => {
    const state = states[index]
    updateState(index, { acting: true, error: null })

    const body: Record<string, unknown> = { index, action }
    if (action === 'accept' && state.editMode) {
      body.term = state.editedTerm
      body.definition = state.editedDefinition
      body.translations = Object.entries(state.editedTranslations)
        .filter(([, v]) => v.trim())
        .map(([language_code, preferred_translation]) => ({ language_code, preferred_translation }))
    }

    const result = await http<{ suggestion: GlossarySuggestion }>({
      method: APIMethod.patch,
      path: `/api/project/${project.id}/glossary/suggestions`,
      data: body,
    })

    updateState(index, { acting: false })

    if (result.value) {
      setSuggestions(prev => prev.map((s, i) => i === index ? result.value!.suggestion : s))
      if (action === 'accept') onAccepted()
    } else if (result.error?.includes('Already reviewed') || result.error?.includes('409')) {
      updateState(index, { error: 'Already reviewed' })
    } else {
      updateState(index, { error: result.error ?? 'Action failed' })
    }
  }

  const statusBadge = (status: GlossarySuggestion['status']) => {
    if (status === 'accepted') return <Badge bg="success">Accepted</Badge>
    if (status === 'rejected') return <Badge bg="secondary">Rejected</Badge>
    return <Badge bg="warning" text="dark">Pending</Badge>
  }

  return (
    <div className="mt-4">
      <h5>AI-suggested terms ({pendingCount} pending)</h5>
      {suggestions.map((suggestion, index) => {
        const state = states[index]
        return (
          <Card key={index} className="mb-2">
            <Card.Header>
              <Stack direction="horizontal" gap={2}>
                {state.editMode
                  ? <Form.Control
                      size="sm"
                      value={state.editedTerm}
                      onChange={e => updateState(index, { editedTerm: e.target.value })}
                      style={{ maxWidth: 200 }}
                    />
                  : <span className="fw-semibold">{suggestion.term}</span>
                }
                {statusBadge(suggestion.status)}
                {suggestion.status === 'pending' && (
                  <>
                    <Button
                      size="sm"
                      variant="success"
                      className="ms-auto"
                      disabled={state.acting}
                      onClick={() => handleAction(index, 'accept')}
                    >
                      Accept
                    </Button>
                    <Button
                      size="sm"
                      variant="outline-secondary"
                      disabled={state.acting}
                      onClick={() => updateState(index, { editMode: !state.editMode })}
                    >
                      ✏
                    </Button>
                    <Button
                      size="sm"
                      variant="outline-danger"
                      disabled={state.acting}
                      onClick={() => handleAction(index, 'reject')}
                    >
                      Reject
                    </Button>
                  </>
                )}
              </Stack>
              {state.error && <Alert variant="danger" className="mb-0 mt-1 py-1 px-2 small">{state.error}</Alert>}
            </Card.Header>
            <Card.Body>
              {state.editMode
                ? <Form.Control
                    as="textarea"
                    rows={2}
                    value={state.editedDefinition}
                    onChange={e => updateState(index, { editedDefinition: e.target.value })}
                    className="mb-2"
                    placeholder="Definition"
                  />
                : suggestion.definition && <p className="mb-2">{suggestion.definition}</p>
              }
              {suggestion.translations.length > 0 && (
                <Table size="sm" bordered className="mb-0">
                  <thead><tr><th>Language</th><th>Translation</th></tr></thead>
                  <tbody>
                    {suggestion.translations.map(t => (
                      <tr key={t.language_code}>
                        <td>{t.language_code}</td>
                        <td>
                          {state.editMode
                            ? <Form.Control
                                size="sm"
                                value={state.editedTranslations[t.language_code] ?? t.preferred_translation}
                                onChange={e => updateState(index, {
                                  editedTranslations: { ...state.editedTranslations, [t.language_code]: e.target.value }
                                })}
                              />
                            : t.preferred_translation
                          }
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        )
      })}
    </div>
  )
}

export default GlossarySuggestionsPanel
