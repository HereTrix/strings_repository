import fileDownload from "js-file-download"
import { FC, JSX, useEffect, useState } from "react"
import { Button, Dropdown, Modal, Stack } from "react-bootstrap"
import { Typeahead } from "react-bootstrap-typeahead"
import { APIMethod, download, http } from "../Utils/network"
import { Bundle } from "../model/Bundle"
import Language from "../model/Language"
import OptionalImage from "../UI/OptionalImage"
import Project from "../model/Project"

type BundleExportModalProps = {
    project: Project
    bundle: Bundle
    show: boolean
    onHide: () => void
}

interface AvailableFormat {
    type: string
    name: string
    extension: string
}

const BundleExportModal: FC<BundleExportModalProps> = ({ project, bundle, show, onHide }): JSX.Element => {
    const [selectedLanguages, setSelectedLanguages] = useState<Language[]>([])
    const [availableFormats, setAvailableFormats] = useState<AvailableFormat[]>()
    const [selectedType, setSelectedType] = useState<AvailableFormat>()
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | undefined>()

    useEffect(() => {
        http<AvailableFormat[]>({
            method: APIMethod.get,
            path: "/api/supported_formats",
        }).then(result => {
            if (result.value) setAvailableFormats(result.value)
        })
    }, [])

    const onExport = async () => {
        if (!selectedType) {
            setError("Select a format")
            return
        }

        setLoading(true)
        setError(undefined)

        const codes = selectedLanguages.map(l => l.code).join(",")
        const params = new Map<string, any>()
        params.set("type", selectedType.type)
        if (codes) params.set("codes", codes)

        const result = await download({
            method: APIMethod.get,
            path: `/api/project/${project.id}/bundles/${bundle.id}/export`,
            params,
        })

        setLoading(false)

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
                <Modal.Title>Export bundle <code>{bundle.version_name}</code></Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Typeahead
                    id="bundle-export-languages"
                    multiple
                    labelKey="name"
                    options={project.languages}
                    placeholder="Choose languages or leave empty for all"
                    onChange={(data) => setSelectedLanguages(data as Language[])}
                    selected={selectedLanguages}
                    renderMenuItemChildren={(item) => {
                        const language = item as Language
                        return (
                            <Stack direction="horizontal" gap={3}>
                                <OptionalImage src={language.img} alt={language.code} width={50} height={38} />
                                <label>{language.name}</label>
                            </Stack>
                        )
                    }}
                />
                <Dropdown className="my-2">
                    <Dropdown.Toggle variant="outline-secondary" id="bundle-export-format">
                        {selectedType ? `${selectedType.name} (${selectedType.extension})` : "Select format"}
                    </Dropdown.Toggle>
                    <Dropdown.Menu>
                        {availableFormats?.map(fmt => (
                            <Dropdown.Item key={fmt.type} onClick={() => setSelectedType(fmt)}>
                                {fmt.name} ({fmt.extension})
                            </Dropdown.Item>
                        ))}
                    </Dropdown.Menu>
                </Dropdown>
                {error && <p className="text-danger mt-2">{error}</p>}
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide}>Cancel</Button>
                <Button onClick={onExport} disabled={loading}>
                    {loading ? "Exporting…" : "Export"}
                </Button>
            </Modal.Footer>
        </Modal>
    )
}

export default BundleExportModal
