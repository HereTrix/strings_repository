import { FC, useRef, useState } from "react"
import { APIMethod, http } from "../../utils/network"
import TokenTranslation, { TokenTranslationsResponse } from "../../types/TokenTranslation"
import { Badge, Button, Dropdown, ListGroup, Row, Spinner, Stack } from "react-bootstrap"
import OptionalImage from "../UI/OptionalImage"
import { EDITABLE_STATUSES, GlossaryHint, PluralForms, getStatusName, getStatusVariant } from "../../types/Translation"
import StringToken from "../../types/StringToken"
import PluralFormsPanel from "../UI/PluralFormsPanel"
import MarkdownField from "../UI/MarkdownField"
import { TMSuggestion } from "../../types/TranslationMemory";
import TranslationMemoryPanel from "../Translation/TranslationMemoryPanel";

type TokenTranslationsPageProps = {
    project_id: number
    token: StringToken
    integrationEnabled: boolean
    open: boolean
}

type TokenTranslationsItemProps = {
    item: TokenTranslation
    default_translation?: string
    default_language?: string
    project_id: number
    integrationEnabled: boolean
    token_key: string
    onSave: (translation: string) => void
    onStatusChange: (status: string) => void
    onPluralSaved: (forms: PluralForms) => void
}

const TokenTranslationsItem: FC<TokenTranslationsItemProps> = ({
    item, default_translation, default_language, project_id, integrationEnabled, token_key, onSave, onStatusChange, onPluralSaved
}) => {
    const [canSave, setCanSave] = useState<boolean>(false)
    const [text, setText] = useState<string>(item.translation)
    const [pluralForms, setPluralForms] = useState<PluralForms>(item.plural_forms ?? {})
    const [pluralsOpen, setPluralsOpen] = useState(false)

    const [suggestion, setSuggestion] = useState<string>('')
    const [translating, setTranslating] = useState(false)

    const [tmSuggestions, setTmSuggestions] = useState<TMSuggestion[] | null>(null)
    const [tmLoading, setTmLoading] = useState(false)
    const [hasFetchedTm, setHasFetchedTm] = useState(false)

    const [error, setError] = useState<string>()

    const ref = useRef<HTMLTextAreaElement>(null)

    const hasPluralForms = Object.keys(pluralForms).length > 0

    const onTranslationChange = (text: string) => {
        setText(text)
        setCanSave(true)
    }

    const onSavePress = () => {
        setCanSave(false)
        onSave(text)
    }

    const useSuggestion = () => {
        onTranslationChange(suggestion)
        setSuggestion('')
    }

    const translate = async () => {
        setTranslating(true)
        setSuggestion('')
        const result = await http<{ translation: string }>({
            method: APIMethod.post,
            path: `/api/project/${project_id}/machine-translate`,
            data: {
                text: default_translation,
                target_language: item.code,
                source_language: default_language,
            },
        })
        setTranslating(false)
        if (result.value) setSuggestion(result.value.translation)
        else setError(result.error ?? 'Translation failed')
    }

    const fetchTmSuggestions = async () => {
        if (hasFetchedTm) return
        setTmLoading(true)
        const result = await http<TMSuggestion[]>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/translation-memory`,
            params: {
                token: token_key,
                language: item.code,
            },
        })
        setTmLoading(false)
        setHasFetchedTm(true)
        if (result.value) {
            setTmSuggestions(result.value)
        } else {
            setTmSuggestions([])
        }
    }

    return (
        <ListGroup.Item className="d-flex justify-content-between align-items-start">
            <Stack>
                <Stack direction="horizontal" gap={2}>
                    <OptionalImage src={item.img} alt={item.code} width={50} height={38} />
                    <label>{item.code}</label>
                    {item.is_default && <Badge bg="info" pill>Default</Badge>}

                    <Dropdown className="ms-auto">
                        <Dropdown.Toggle variant={getStatusVariant(item.status)} size="sm">
                            {getStatusName(item.status)}
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

                <Row>
                    <MarkdownField value={text} onChange={onTranslationChange} />
                    <Stack direction="horizontal" gap={2} className="my-1">
                        {canSave && <Button onClick={onSavePress} className="my-1">Save</Button>}
                        {integrationEnabled && !item.is_default && (
                            <Button
                                variant="outline-primary"
                                size="sm"
                                onClick={translate}
                                disabled={translating}
                            >
                                {translating
                                    ? <><Spinner size="sm" className="me-1" />Translating...</>
                                    : 'Translate'
                                }
                            </Button>
                        )}
                        <Button
                            variant="outline-primary"
                            size="sm"
                            onClick={fetchTmSuggestions}
                            disabled={hasFetchedTm}
                        >
                            {tmLoading
                                ? <><Spinner size="sm" className="me-1" />Fetching...</>
                                : 'Memory'
                            }
                        </Button>
                    </Stack>
                    {suggestion && (
                        <Stack direction="horizontal" gap={2} className="mt-1 p-2 rounded border" style={{ background: '#f0f7ff' }}>
                            <span className="small flex-grow-1">{suggestion}</span>
                            <Button size="sm" variant="outline-success" onClick={useSuggestion}>Use</Button>
                            <Button size="sm" variant="outline-secondary" onClick={() => setSuggestion('')}>✕</Button>
                        </Stack>
                    )}
                    {(tmLoading || (tmSuggestions !== null && tmSuggestions.length > 0)) && (
                        <TranslationMemoryPanel
                            suggestions={tmSuggestions ?? []}
                            loading={tmLoading}
                            onUseSuggestion={(text) => {
                                onTranslationChange(text)
                            }}
                        />
                    )}
                </Row>
                {error && <span className="text-danger small">{error}</span>}

                {pluralsOpen && (
                    <PluralFormsPanel
                        token={token_key}
                        project_id={String(project_id)}
                        code={item.code}
                        baseTranslation={text}
                        initialForms={pluralForms}
                        onSaved={(forms) => {
                            setPluralForms(forms)
                            onPluralSaved(forms)
                        }}
                        onError={setError}
                    />
                )}
            </Stack>
        </ListGroup.Item>
    )
}

const TokenTranslationsView: FC<TokenTranslationsPageProps> = ({ project_id, token, integrationEnabled, open }) => {
    const [translations, setTranslations] = useState<TokenTranslation[]>()
    const [glossaryHints, setGlossaryHints] = useState<GlossaryHint[]>([])
    const [defaultTranslation, setDefaultTranslation] = useState<string>()
    const [defaultLanguageCode, setDefaultLanguageCode] = useState<string>()

    const [error, setError] = useState<string>()

    const updateInList = (code: string, changes: Partial<TokenTranslation>) => {
        setTranslations(prev => prev?.map(t => t.code === code ? { ...t, ...changes } : t))
        if (changes.translation && code === defaultLanguageCode) {
            setDefaultTranslation(changes.translation)
        }
    }

    const load = async () => {
        const result = await http<TokenTranslationsResponse>({
            method: APIMethod.get,
            path: `/api/string_token/${token.id}/translations`
        })
        if (result.value) {
            setTranslations(result.value.translations)
            setGlossaryHints(result.value.glossary_hints)
            setDefaultLanguageCode(result.value.default_language)
            setDefaultTranslation(result.value.default_translation)
        }
    }

    const saveTranslation = async (code: string, translation: string) => {
        const result = await http<TokenTranslation>({
            method: APIMethod.post,
            path: "/api/translation",
            data: { project_id, code, token: token.token, translation }
        })
        if (result.error) setError(result.error)
        if (result.value) {
            const updatedTranslation = result.value
            updateInList(code, { translation, status: updatedTranslation.status })
        }
    }

    const updateTranslationStatus = async (item: TokenTranslation, newStatus: string) => {
        const previousStatus = item.status
        updateInList(item.code, { status: newStatus })
        const result = await http({
            method: APIMethod.put,
            path: `/api/translation/status`,
            data: { project_id, code: item.code, token: token.token, status: newStatus }
        })
        if (result.error) {
            setError(result.error)
            updateInList(item.code, { status: previousStatus })
        }
    }

    if (open && !translations) {
        load()
    }

    return (
        <ListGroup className="my-2">
            {error && <span className="text-danger small px-2">{error}</span>}
            {glossaryHints.length > 0 && (
                <ListGroup.Item className="py-1 px-2 small" style={{ background: 'var(--bs-tertiary-bg)' }}>
                    <span className="fw-semibold text-muted me-2">Glossary:</span>
                    {glossaryHints.map((hint: GlossaryHint) => (
                        <span key={hint.term} className="me-3">
                            <span className="text-muted">{hint.term}</span>
                            {hint.definition && (
                                <span className="text-muted fst-italic ms-1">— {hint.definition}</span>
                            )}
                        </span>
                    ))}
                </ListGroup.Item>
            )}
            {translations?.map((item) => (
                <TokenTranslationsItem
                    key={item.code}
                    item={item}
                    default_language={defaultLanguageCode}
                    default_translation={defaultTranslation}
                    project_id={project_id}
                    integrationEnabled={integrationEnabled}
                    token_key={token.token}
                    onSave={(translation) => saveTranslation(item.code, translation)}
                    onStatusChange={(status) => updateTranslationStatus(item, status)}
                    onPluralSaved={(forms) => updateInList(item.code, { plural_forms: forms })}
                />
            ))}
        </ListGroup>
    )
}

export default TokenTranslationsView