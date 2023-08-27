import { FC, useEffect, useState } from "react"
import { Button, Col, Modal, Row } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import Language from "../model/Language"
import { Typeahead } from "react-bootstrap-typeahead"

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
                <Row>
                    <Typeahead
                        id="basic-typeahead-single"
                        labelKey="name"
                        options={available}
                        placeholder="Choose a country..."
                        onChange={(data) => { setSelectedLanguages(data as Language[]) }}
                        selected={selectedLanguages}
                        renderMenuItemChildren={(item) => {

                            var language = item as Language
                            return (
                                <Row >
                                    <Col>
                                        <img src={"/static/flags/" + language.code.toLocaleLowerCase() + ".png"} alt={language.code} />
                                    </Col>
                                    <Col>
                                        <label className="align-items-center">{language.name}</label>
                                    </Col>
                                </Row>
                            )
                        }}
                    />
                </Row>
                <Button type="submit" className="mb-3" onClick={submit}>Save</Button>
            </Modal.Body>
        </Modal>
    )
}

export default AddLaguagePage