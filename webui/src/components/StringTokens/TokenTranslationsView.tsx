import { ChangeEventHandler, FC, useRef, useState } from "react"
import { APIMethod, http } from "../../utils/network"
import TokenTranslation from "../../types/TokenTranslation"
import { Badge, Button, Container, Dropdown, ListGroup, Stack } from "react-bootstrap"
import OptionalImage from "../UI/OptionalImage"
import { EDITABLE_STATUSES, PluralForms, getStatusName, getStatusVariant } from "../../types/Translation"
import StringToken from "../../types/StringToken"
import PluralFormsPanel from "../UI/PluralFormsPanel"
import MarkdownField from "../UI/MarkdownField"

type TokenTranslationsPageProps = {
    project_id: number
    token: StringToken
    open: boolean
}

type TokenTranslationsItemProps = {
    item: TokenTranslation
    project_id: number
    token_key: string
    onSave: (translation: string) => void
    onStatusChange: (status: string) => void
    onPluralSaved: (forms: PluralForms) => void
}

const TokenTranslationsItem: FC<TokenTranslationsItemProps> = ({
    item, project_id, token_key, onSave, onStatusChange, onPluralSaved
}) => {
    const [canSave, setCanSave] = useState<boolean>(false)
    const [text, setText] = useState<string>(item.translation)
    const [pluralForms, setPluralForms] = useState<PluralForms>(item.plural_forms ?? {})
    const [pluralsOpen, setPluralsOpen] = useState(false)
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

    return (
        <ListGroup.Item className="d-flex justify-content-between align-items-start">
            <Stack>
                <Stack direction="horizontal" gap={2}>
                    <OptionalImage src={item.img} alt={item.code} width={50} height={38} />
                    <label>{item.code}</label>

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

                <Stack className="w-100 p-2">
                    <MarkdownField value={text} onChange={onTranslationChange} />
                </Stack>
                {canSave && <Button onClick={onSavePress} className="my-1">Save</Button>}
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

const TokenTranslationsView: FC<TokenTranslationsPageProps> = ({ project_id, token, open }) => {
    const [translations, setTranslations] = useState<TokenTranslation[]>()
    const [error, setError] = useState<string>()

    const updateInList = (code: string, changes: Partial<TokenTranslation>) => {
        console.log('Updating translation in list', code, changes, translations)
        setTranslations(prev => prev?.map(t => t.code === code ? { ...t, ...changes } : t))
    }

    const load = async () => {
        const result = await http<TokenTranslation[]>({
            method: APIMethod.get,
            path: `/api/string_token/${token.id}/translations`
        })
        if (result.value) {
            setTranslations(result.value)
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
            {translations?.map((item) => (
                <TokenTranslationsItem
                    key={item.code}
                    item={item}
                    project_id={project_id}
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