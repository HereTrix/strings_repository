import fileDownload from "js-file-download";
import { FC, useEffect, useState } from "react";
import { Button, Col, Dropdown, DropdownButton, Modal, Row, Stack } from "react-bootstrap";
import { download, APIMethod, http } from "../Utils/network";
import Project from "../model/Project";
import { Typeahead } from "react-bootstrap-typeahead";
import Language from "../model/Language";
import OptionalImage from "../UI/OptionalImage";

type ExportPageProps = {
    project: Project
    code?: string | undefined
    show: boolean
    onHide: () => void
}

interface AvailableFormat {
    type: number
    name: string
    extension: string
}

const ExportPage: FC<ExportPageProps> = ({ project, code, show, onHide }): JSX.Element => {

    const [selectedLanguages, setSelectedLanguages] = useState<Language[]>([])
    const [availableFormats, setAvailableFormats] = useState<AvailableFormat[]>()
    const [selectedType, setSelectedType] = useState<AvailableFormat>()
    const [selectedTags, setSelectedTags] = useState<string[]>()

    const [tags, setTags] = useState<string[]>([])

    const [error, setError] = useState<string | undefined>()

    const fetchTypes = async () => {
        const result = await http<AvailableFormat[]>({
            method: APIMethod.get,
            path: "/api/supported_formats"
        })

        if (result.value) {
            setAvailableFormats(result.value)
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
        const lang = project.languages.find((lang) => lang.code.toLowerCase() == code?.toLowerCase())
        if (lang) {
            setSelectedLanguages([lang])
        }
        fetchTypes()
        fetchTags()
    }, [])

    const onExport = async () => {
        if (!selectedType) {
            setError("Select type")
            return
        }

        setError(undefined)

        const codes = selectedLanguages.map((lang) => lang.code).join(",")

        var params = new Map<string, any>()
        params.set('codes', codes)
        params.set('project_id', project.id)
        if (selectedType) {
            params.set('type', selectedType.type)
        }

        if (selectedTags) {
            params.set('tags', selectedTags.join(","))
        }

        const result = await download({
            method: APIMethod.get,
            path: '/api/export',
            params: params
        })

        if (result.value) {
            fileDownload(result.value.content, result.value.name)
            onHide()
        } else {
            setError(result.error)
        }
    }

    return (
        <Modal show={show} onHide={onHide}>
            <Modal.Header closeButton>
                <Modal.Title>Add project</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Typeahead
                    id="basic-typeahead-single"
                    multiple
                    labelKey="name"
                    options={project.languages}
                    placeholder="Choose languages or leave empty for all"
                    onChange={(data) => { setSelectedLanguages(data as Language[]) }}
                    selected={selectedLanguages}
                    renderMenuItemChildren={(item) => {

                        var language = item as Language
                        return (
                            <Stack direction="horizontal" gap={3}>
                                <OptionalImage
                                    src={`/static/flags/${language.code.toLocaleLowerCase()}.png`}
                                    alt={language.code} />
                                <label className="align-items-center">{language.name}</label>

                            </Stack>
                        )
                    }}
                />
                <Typeahead
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
                <Dropdown className="my-2">
                    <Dropdown.Toggle variant="success" id="dropdown-basic">
                        {selectedType ? selectedType.name : "Select format"}
                    </Dropdown.Toggle>
                    <Dropdown.Menu>
                        {availableFormats && availableFormats.map((format) => {
                            return (
                                <Dropdown.Item onClick={() => setSelectedType(format)} key={format.type}>{`${format.name} (${format.extension})`}</Dropdown.Item>
                            )
                        })}
                    </Dropdown.Menu>
                </Dropdown>
                {error &&
                    <Row className="my-3">
                        <label className="error">{error}</label>
                    </Row>
                }
                <Button
                    onClick={onExport}
                    className="my-2"
                >
                    Export
                </Button>
            </Modal.Body>
        </Modal>
    )
}

export default ExportPage