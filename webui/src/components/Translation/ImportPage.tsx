import { FC, useEffect, useState } from "react"
import Project, { ProjectRole } from "../../types/Project"
import { Alert, Button, Dropdown, Form, Modal } from "react-bootstrap"
import { SubmitHandler, useForm } from "react-hook-form"
import ErrorAlert from "../UI/ErrorAlert"
import { APIMethod, http, upload } from "../../utils/network"
import { Typeahead } from "react-bootstrap-typeahead"
import { useNavigate } from "react-router-dom"

type ImportPageProps = {
    project: Project
    code?: string
    show: boolean
    onHide: () => void
}

type Inputs = {
    file: FileList
}

interface ImportResult {
    imported: number
    deprecated: number
}

const canDeprecateMissing = (role: ProjectRole) =>
    role === ProjectRole.owner || role === ProjectRole.admin

const ImportPage: FC<ImportPageProps> = ({ project, code, show, onHide }) => {

    const navigate = useNavigate()

    const [error, setError] = useState<string>()
    const [tags, setTags] = useState<string[]>([])
    const [result, setResult] = useState<ImportResult | undefined>()

    const [selectedTags, setSelectedTags] = useState<string[]>()
    const [selectedLanguage, setSelectedLanguage] = useState<string | undefined>(code)
    const [deprecateMissing, setDeprecateMissing] = useState(false)

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {
        setResult(undefined)

        if (!selectedLanguage) {
            setError("Language should be selected")
            return
        }

        if (!data.file) {
            setError("File should be selected")
            return
        }

        const tagToSend: string[] = selectedTags ?? []

        const result = await upload<ImportResult>({
            method: APIMethod.post,
            path: `/api/import`,
            data: {
                "file": data.file[0],
                "code": selectedLanguage,
                "tags": tagToSend,
                "project_id": project.id,
                "deprecate_missing": deprecateMissing ? "true" : "false",
            }
        })

        if (result.value) {
            setResult(result.value)
        } else {
            setError(result.error)
        }
    }

    const fetchTags = async () => {
        const result = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/tags`
        })

        if (result.value) {
            setTags(result.value)
        }
    }

    useEffect(() => {
        fetchTags()
    }, [])

    return (
        <Modal show={show} onHide={onHide}>
            <Modal.Header closeButton>
                <Modal.Title>Import translations</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form
                    onSubmit={handleSubmit(onSubmit)}
                    className="container my-2"
                >
                    <Form.Group>

                        <Form.Control
                            type="file"
                            {...register("file", { required: "File is required", })}
                        />
                        <Dropdown className="my-2">
                            <Dropdown.Toggle variant="success" id="dropdown-basic">
                                {selectedLanguage ? selectedLanguage : "Language to import"}
                            </Dropdown.Toggle>
                            <Dropdown.Menu>
                                {project.languages.map((itm) =>
                                    <Dropdown.Item onClick={() => setSelectedLanguage(itm.code)}
                                        key={itm.code}
                                    >{itm.name}</Dropdown.Item>
                                )}
                            </Dropdown.Menu>
                        </Dropdown>
                        <Typeahead
                            allowNew
                            newSelectionPrefix="Select or create tag: "
                            id="basic-typeahead-multiple"
                            multiple
                            labelKey={"tag"}
                            options={tags}
                            placeholder="Select tags..."
                            onChange={(data) => {
                                setSelectedTags(
                                    data.map((val: any) => typeof val === 'string' ? val : val.tag)
                                )
                            }}
                            selected={selectedTags}
                            className="my-2"
                        />
                        {canDeprecateMissing(project.role) && (
                            <Form.Group className="my-2">
                                <Form.Check
                                    type="checkbox"
                                    id="deprecate-missing"
                                    label="Mark missing tokens as deprecated"
                                    checked={deprecateMissing}
                                    onChange={(e) => setDeprecateMissing(e.target.checked)}
                                    disabled={!!selectedTags?.length}
                                />
                                {deprecateMissing && (
                                    <Form.Text className="text-warning d-block">
                                        All active tokens not present in the imported file will be marked as deprecated.
                                        Cannot be used with tag filters.
                                    </Form.Text>
                                )}
                                {!!selectedTags?.length && (
                                    <Form.Text className="text-muted d-block">
                                        Unavailable when tag filter is active.
                                    </Form.Text>
                                )}
                            </Form.Group>
                        )}
                        <Button
                            type="submit"
                            className="my-2"
                        >Import</Button>
                    </Form.Group>
                </Form>
                {result && (
                    <Alert variant="success" className="mx-2">
                        Imported {result.imported} translation{result.imported !== 1 ? 's' : ''}.
                        {result.deprecated > 0 && ` Marked ${result.deprecated} token${result.deprecated !== 1 ? 's' : ''} as deprecated.`}
                    </Alert>
                )}
            </Modal.Body>
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </Modal>
    )
}

export default ImportPage