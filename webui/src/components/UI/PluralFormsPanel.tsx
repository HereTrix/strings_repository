import { Button, Stack } from "react-bootstrap"
import { PLURAL_FORM_ORDER, PluralForms } from "../../types/Translation"
import { FC, useState } from "react"
import { APIMethod, http } from "../../utils/network"
import DiffView from "./DiffView"

type PluralFormsPanelProps = {
    token: string
    project_id: string
    code: string
    baseTranslation: string
    initialForms: PluralForms
    onSaved: (forms: PluralForms) => void
    onError: (msg: string) => void
}

const PluralFormsPanel: FC<PluralFormsPanelProps> = ({
    token, project_id, code, baseTranslation, initialForms, onSaved, onError
}) => {
    const [forms, setForms] = useState<PluralForms>({ ...initialForms })
    const [canSave, setCanSave] = useState(false)
    const [saveSuccess, setSaveSuccess] = useState(false)
    const [diffForm, setDiffForm] = useState<keyof PluralForms | null>(null)

    const onChange = (form: keyof PluralForms, value: string) => {
        setForms(prev => ({ ...prev, [form]: value }))
        setCanSave(true)
        setSaveSuccess(false)
    }

    const save = async () => {
        const result = await http({
            method: APIMethod.put,
            path: '/api/plural',
            data: { project_id, code, token, plural_forms: forms },
        })
        if (result.error) {
            onError(result.error)
        } else {
            setCanSave(false)
            setSaveSuccess(true)
            onSaved(forms)
        }
    }

    return (
        <div className="mt-2 ps-2 border-start border-2 border-info">
            {PLURAL_FORM_ORDER.map(form => {
                const value = forms[form] ?? ''
                const isDiffing = diffForm === form
                const hasDiff = !!baseTranslation && !!value && value !== baseTranslation

                return (
                    <div key={form} className="mb-3">
                        <Stack direction="horizontal" gap={2} className="mb-1">
                            <span className="text-muted small fw-semibold" style={{ minWidth: '3rem' }}>
                                {form}
                            </span>
                            {hasDiff && (
                                <Button
                                    variant={isDiffing ? 'info' : 'outline-info'}
                                    size="sm"
                                    style={{ fontSize: '0.75em', padding: '1px 6px' }}
                                    onClick={() => setDiffForm(isDiffing ? null : form)}
                                >
                                    {isDiffing ? 'Hide diff' : 'Diff'}
                                </Button>
                            )}
                        </Stack>

                        {isDiffing && hasDiff && (
                            <div
                                className="mb-1 p-2 rounded border"
                                style={{ background: 'var(--bs-tertiary-bg)' }}
                            >
                                <DiffView base={baseTranslation} next={value} />
                            </div>
                        )}

                        <textarea
                            className="form-control form-control-sm"
                            rows={2}
                            style={{ resize: 'vertical' }}
                            value={value}
                            onChange={e => onChange(form, e.target.value)}
                        />
                    </div>
                )
            })}

            <Stack direction="horizontal" gap={2}>
                {canSave && <Button size="sm" onClick={save}>Save plurals</Button>}
                {!canSave && saveSuccess && <span className="text-success small">✓ Saved</span>}
            </Stack>
        </div>
    )
}

export default PluralFormsPanel