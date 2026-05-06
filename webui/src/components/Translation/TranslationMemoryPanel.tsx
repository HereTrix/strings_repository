import { FC } from 'react'
import { Badge, Button, Spinner, Stack } from 'react-bootstrap'
import { TMSuggestion } from '../../types/TranslationMemory'

interface TranslationMemoryPanelProps {
  suggestions: TMSuggestion[]
  loading: boolean
  onUseSuggestion: (translationText: string) => void
}

const TRUNCATE = 200

function truncate(text: string): string {
  return text.length > TRUNCATE ? text.slice(0, TRUNCATE) + '…' : text
}

const TranslationMemoryPanel: FC<TranslationMemoryPanelProps> = ({
  suggestions,
  loading,
  onUseSuggestion,
}) => {
  if (!loading && suggestions.length === 0) return null

  return (
    <div
      className="mt-2 p-2 rounded border"
      style={{ background: 'var(--bs-tertiary-bg, #f8f9fa)' }}
    >
      <div className="small fw-semibold text-muted mb-1">Similar strings</div>
      {loading && suggestions.length === 0 && (
        <div className="text-muted small d-flex align-items-center gap-2">
          <Spinner size="sm" />
          <span>Looking for similar strings…</span>
        </div>
      )}
      {suggestions.map((s, i) => (
        <Stack
          key={i}
          direction="horizontal"
          gap={2}
          className="py-1 border-bottom align-items-start"
          style={{ borderColor: 'var(--bs-border-color)' }}
        >
          <div className="flex-grow-1" style={{ minWidth: 0 }}>
            <div className="small text-muted" style={{ wordBreak: 'break-word' }}>
              <span className="fw-semibold me-1">{s.token_key}:</span>
              {truncate(s.source_text)}
            </div>
            <div className="small" style={{ wordBreak: 'break-word' }}>
              {truncate(s.translation_text)}
            </div>
          </div>
          <div className="d-flex flex-column align-items-end gap-1 flex-shrink-0">
            <Badge bg="secondary" className="text-nowrap">
              {Math.round(s.similarity_score * 100)}%
            </Badge>
            <Button
              size="sm"
              variant="outline-success"
              onClick={() => onUseSuggestion(s.translation_text)}
            >
              Use
            </Button>
          </div>
        </Stack>
      ))}
    </div>
  )
}

export default TranslationMemoryPanel
