import { FC, useEffect, useState } from "react"
import Project from "../model/Project"
import { Button, Dropdown, Form, Modal } from "react-bootstrap"
import Language from "../model/Language"
import { SubmitHandler, useForm } from "react-hook-form"
import ErrorAlert from "../UI/ErrorAlert"
import { APIMethod, http, upload } from "../Utils/network"
import { Typeahead } from "react-bootstrap-typeahead"

type ImportPageProps = {
    project: Project
    code?: string
    show: boolean
    onHide: () => void
}

type Inputs = {
    file: FileList
}

const ImportPage: FC<ImportPageProps> = ({ project, code, show, onHide }) => {

    const [error, setError] = useState<string>()
    const [tags, setTags] = useState<string[]>([])

    const [selectedTags, setSelectedTags] = useState<string[]>()
    const [selectedLanguage, setSelectedLanguage] = useState<string | undefined>(code)

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {

        if (!selectedLanguage) {
            setError("Language should be selected")
            return
        }

        if (!data.file) {
            setError("File should be selected")
        }

        var tagToSend: string[] = []
        if (selectedTags) {
            tagToSend = selectedTags
        }

        const result = await upload({
            method: APIMethod.post,
            path: `/api/import`,
            data: {
                "file": data.file[0],
                "code": selectedLanguage,
                "tags": tagToSend,
                "project_id": project.id
            }
        })

        if (result.value) {
            onHide()
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
                            newSelectionPrefix="Select pr create tag: "
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
                        <Button
                            type="submit"
                            className="my-2"
                        >Import</Button>
                    </Form.Group>
                </Form>
            </Modal.Body>
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </Modal>
    )
}

export default ImportPage