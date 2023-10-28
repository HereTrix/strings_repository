import { FC, useEffect, useState } from "react"
import { Button, Col, Modal, Row, Stack } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import Language from "../model/Language"
import { Typeahead } from "react-bootstrap-typeahead"
import OptionalImage from "../UI/OptionalImage"

type AddLaguagePageProps = {
    project_id: number
    show: boolean
    onHide: () => void
    onSuccess: () => void
}

const AddLaguagePage: FC<AddLaguagePageProps> = ({ project_id, show, onHide, onSuccess }) => {

    const [available, setAvailable] = useState<Language[]>([])

    const [selectedLanguages, setSelectedLanguages] = useState<Language[]>([])

    const submit = async () => {
        if (selectedLanguages.length == 0) {
            return
        }
        const language = selectedLanguages[0]

        const result = await http({
            method: APIMethod.post,
            path: "/api/language",
            data: { "project": project_id, "code": language.code }
        })

        console.log(result)
        if (result.error) {

        } else {
            onSuccess()
            onHide()
        }
    }

    const fetch = async () => {
        const data = await http<Language[]>({
            method: APIMethod.get,
            path: "/api/project/" + project_id + "/availableLanguages"
        })

        if (data.value) {
            setAvailable(data.value)
        } else {

        }
    }

    useEffect(() => {
        fetch()
    }, [])


    return (
        <Modal show={show} onHide={onHide}>
            <Modal.Header closeButton>
                <Modal.Title>Add language</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Row className="my-2">
                    <Typeahead
                        id="basic-typeahead-single"
                        labelKey="name"
                        options={available}
                        placeholder="Choose a language..."
                        onChange={(data) => { setSelectedLanguages(data as Language[]) }}
                        selected={selectedLanguages}
                        renderMenuItemChildren={(item) => {

                            var language = item as Language
                            return (
                                <Stack direction="horizontal" gap={3}>
                                    <OptionalImage image={`/static/flags/${language.code.toLocaleLowerCase()}.png`} alt={language.code.toUpperCase()} />
                                    <label className="align-items-center display-linebreak">{language.name}</label>
                                </Stack>
                            )
                        }}
                    />
                </Row>
                <Button type="submit" className="my-2" onClick={submit}>Save</Button>
            </Modal.Body>
        </Modal>
    )
}

export default AddLaguagePage