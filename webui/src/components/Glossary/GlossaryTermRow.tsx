import { FC } from "react"
import { Badge, Button } from "react-bootstrap"
import { GlossaryTerm } from "../../types/Glossary"

interface GlossaryTermRowProps {
  term: GlossaryTerm
  canManage: boolean
  onEdit: (term: GlossaryTerm) => void
  onDelete: (term: GlossaryTerm) => void
}

const GlossaryTermRow: FC<GlossaryTermRowProps> = ({ term, canManage, onEdit, onDelete }) => {
  const definition = term.definition.length > 100
    ? term.definition.slice(0, 100) + '…'
    : term.definition

  return (
    <tr>
      <td>
        {term.term}
        {term.case_sensitive && (
          <Badge bg="secondary" className="ms-1 small">case-sensitive</Badge>
        )}
      </td>
      <td title={term.definition}>{definition}</td>
      <td>
        {term.translations.length > 0
          ? term.translations.map(tr => (
              <Badge key={tr.language_code} bg="info" className="me-1">{tr.language_code}</Badge>
            ))
          : <span className="text-muted">—</span>
        }
      </td>
      {canManage && (
        <td>
          <Button
            variant="outline-secondary"
            size="sm"
            className="me-1"
            onClick={() => onEdit(term)}
          >
            Edit
          </Button>
          <Button
            variant="outline-danger"
            size="sm"
            onClick={() => onDelete(term)}
          >
            Delete
          </Button>
        </td>
      )}
    </tr>
  )
}

export default GlossaryTermRow
