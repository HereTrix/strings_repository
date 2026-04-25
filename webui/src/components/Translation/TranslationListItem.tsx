import { Badge, Button, Dropdown, ListGroup, Row, Spinner, Stack } from "react-bootstrap"
import PluralFormsPanel from "../UI/PluralFormsPanel"
import DiffView from "../UI/DiffView"
import Translation, { EDITABLE_STATUSES, getStatusName, getStatusVariant, PluralForms, TranslationModel } from "../../types/Translation"
import { FC, useEffect, useRef, useState } from "react"
import TagsContainer from "../UI/TagsContainer"
import MarkdownField from "../UI/MarkdownField"
import { APIMethod, http } from "../../utils/network"

type TranslationListItemProps = {
    translation: TranslationModel
    selectedTags: string[]
    project_id: string
    code: string
    defaultLanguageCode?: string
    integrationEnabled: boolean
    onSave: (translation: Translation) => void
    onStatusChange: (status: string) => void
    onTagClick: (tag: string) => void
    onError: (msg: string) => void
}

const TranslationListItem: FC<TranslationListItemProps> = ({
    translation, selectedTags, project_id, code, defaultLanguageCode, integrationEnabled,
    onSave, onStatusChange, onTagClick, onError
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
    const [suggestion, setSuggestion] = useState<string>()
    const [translating, setTranslating] = useState(false)

    const ref = useRef<HTMLTextAreaElement>(null)

    const hasPluralForms = Object.keys(pluralForms).length > 0

    // Sync text if translation prop changes externally (e.g. optimistic revert)
    useEffect(() => {
        setText(translation.translation)
        setSavedText(translation.translation)
    }, [translation.translation])

    const onTranslationChange = (text: string) => {
        setText(text)
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

    const translate = async () => {
        setTranslating(true)
        setSuggestion(undefined)
        const result = await http<{ translation: string }>({
            method: APIMethod.post,
            path: `/api/project/${project_id}/machine-translate`,
            data: {
                text: translation.default_translation,
                target_language: code,
                source_language: defaultLanguageCode,
            },
        })
        setTranslating(false)
        if (result.value) setSuggestion(result.value.translation)
        else onError(result.error ?? 'Translation failed')
    }

    const useSuggestion = () => {
        setText(suggestion)
        setCanSave(true)
        setSaveSuccess(false)
        setSuggestion(undefined)
    }

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

                {translation.default_translation && (
                    <div className="my-1 px-2 py-1 rounded border text-muted small" style={{ background: '#f8f9fa' }}>
                        <span className="fw-semibold me-1">{defaultLanguageCode ?? 'Default'}:</span>
                        {translation.default_translation}
                    </div>
                )}

                <Row>
                    <MarkdownField value={text ?? ''}
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
                        {integrationEnabled && translation.default_translation && (
                            <Button
                                variant="outline-primary"
                                size="sm"
                                onClick={translate}
                                disabled={translating}
                            >
                                {translating
                                    ? <><Spinner size="sm" className="me-1" />Translating…</>
                                    : 'Translate'
                                }
                            </Button>
                        )}
                    </Stack>
                    {suggestion && (
                        <Stack direction="horizontal" gap={2} className="mt-1 p-2 rounded border" style={{ background: '#f0f7ff' }}>
                            <span className="small flex-grow-1">{suggestion}</span>
                            <Button size="sm" variant="outline-success" onClick={useSuggestion}>Use</Button>
                            <Button size="sm" variant="outline-secondary" onClick={() => setSuggestion(undefined)}>✕</Button>
                        </Stack>
                    )}
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