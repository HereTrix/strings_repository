import { Badge, Button, Dropdown, ListGroup, Row, Stack } from "react-bootstrap"
import PluralFormsPanel from "../UI/PluralFormsPanel"
import DiffView from "../UI/DiffView"
import Translation, { EDITABLE_STATUSES, getStatusName, getStatusVariant, PluralForms, TranslationModel } from "../model/Translation"
import { ChangeEventHandler, FC, useEffect, useState } from "react"
import TagsContainer from "../UI/TagsContainer"

type TranslationListItemProps = {
    translation: TranslationModel
    selectedTags: string[]
    project_id: string
    code: string
    onSave: (translation: Translation) => void
    onStatusChange: (status: string) => void
    onTagClick: (tag: string) => void
    onError: (msg: string) => void
}

const TranslationListItem: FC<TranslationListItemProps> = ({
    translation, selectedTags, project_id, code, onSave, onStatusChange, onTagClick, onError
}) => {
    const [canSave, setCanSave] = useState<boolean>(false)
    const [saveSuccess, setSaveSuccess] = useState<boolean>(false)
    const [text, setText] = useState<string | undefined>(translation.translation)
    const [savedText, setSavedText] = useState<string | undefined>(translation.translation)
    const [showDiff, setShowDiff] = useState(false)
    const [pluralForms, setPluralForms] = useState<PluralForms>(
        (translation as any).plural_forms ?? {}
    )
    const [pluralsOpen, setPluralsOpen] = useState(false)

    const hasPluralForms = Object.keys(pluralForms).length > 0

    // Sync text if translation prop changes externally (e.g. optimistic revert)
    useEffect(() => {
        setText(translation.translation)
        setSavedText(translation.translation)
    }, [translation.translation])

    const onTranslationChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
        setText(event.target.value)
        setCanSave(true)
        setSaveSuccess(false)
    }

    const save = () => {
        setCanSave(false)
        setSaveSuccess(true)
        setShowDiff(false)
        setSavedText(text)
        const newTranslation: Translation = { token: translation.token, translation: text }
        onSave(newTranslation)
    }

    const hasDiff = canSave && !!savedText && savedText !== text

    return (
        <ListGroup.Item>
            <Stack>
                <Stack direction="horizontal" gap={4}>
                    <span>{translation.token}</span>
                    {translation.tags &&
                        <TagsContainer
                            tags={translation.tags}
                            selectedTags={selectedTags}
                            onTagClick={onTagClick}
                        />}
                    <Dropdown>
                        <Dropdown.Toggle variant={getStatusVariant(translation.status)} size="sm">
                            {getStatusName(translation.status)}
                        </Dropdown.Toggle>
                        <Dropdown.Menu>
                            {EDITABLE_STATUSES.map(status => (
                                <Dropdown.Item
                                    key={status}
                                    active={false}
                                    onClick={() => onStatusChange(status)}
                                >
                                    <Badge bg={getStatusVariant(status)} className="me-2">
                                        {getStatusName(status)}
                                    </Badge>
                                    {getStatusName(status)}
                                </Dropdown.Item>
                            ))}
                        </Dropdown.Menu>
                    </Dropdown>
                    <Button
                        variant={pluralsOpen ? 'info' : 'outline-info'}
                        size="sm"
                        onClick={() => setPluralsOpen(o => !o)}
                    >
                        {hasPluralForms
                            ? `Plurals (${Object.keys(pluralForms).length})`
                            : '+ Plurals'}
                    </Button>
                </Stack>

                {showDiff && hasDiff && (
                    <div className="my-1 p-2 rounded border" style={{ background: '#f8f9fa' }}>
                        <DiffView base={savedText!} next={text ?? ''} />
                    </div>
                )}

                <Row>
                    <textarea
                        rows={3}
                        style={{ resize: 'vertical' }}
                        value={text ?? ''}
                        onChange={onTranslationChange}
                    />
                    <Stack direction="horizontal" gap={2} className="my-1">
                        {hasDiff && (
                            <Button
                                variant={showDiff ? 'secondary' : 'outline-secondary'}
                                size="sm"
                                onClick={() => setShowDiff(v => !v)}
                            >
                                {showDiff ? 'Hide diff' : 'Diff'}
                            </Button>
                        )}
                        {canSave && <Button onClick={save}>Save</Button>}
                        {!canSave && saveSuccess && (
                            <span className="text-success small">✓ Saved</span>
                        )}
                    </Stack>
                </Row>

                {pluralsOpen && (
                    <PluralFormsPanel
                        token={translation.token}
                        project_id={project_id}
                        code={code}
                        baseTranslation={text ?? ''}
                        initialForms={pluralForms}
                        onSaved={setPluralForms}
                        onError={onError}
                    />
                )}
            </Stack>
        </ListGroup.Item>
    )
}

export default TranslationListItem