import { FC, useEffect, useState } from "react"
import { Button, Container, ListGroup, Row } from "react-bootstrap"
import AddLaguagePage from "./AddLaguagePage"
import Language from "../model/Language"
import Project from "../model/Project"
import { APIMethod, http } from "../Utils/network"

type LanguagesProps = {
    project: Project
}

type LanguageListItemProp = {
    language: Language
    project_id: number
    onDelete: () => void
}

const LanguageListItem: FC<LanguageListItemProp> = ({ language, project_id, onDelete }): JSX.Element => {

    return (
        <ListGroup.Item
            href={"/project/" + project_id + "/language/" + language.code.toLocaleLowerCase()}
            action
            className="d-flex justify-content-between align-items-start">
            <img className="icon" src={"/static/flags/" + language.code.toLocaleLowerCase() + ".png"} alt={language.code} />
            <label>{language.name}</label>
            <Button onClick={onDelete}>Delete</Button>
        </ListGroup.Item>
    )
}

const LanguagesList: FC<LanguagesProps> = ({ project }) => {

    const [languages, setLanguages] = useState<Language[]>()
    const [showDialog, setShowDialog] = useState(false)

    const deleteLanguage = async (language: Language) => {
        const result = await http({
            method: APIMethod.delete,
            path: "/api/language",
            data: { "project": project.id, "code": language.code }
        })

        if (result.error) {

        } else {
            load()
        }
    }

    const load = async () => {
        const result = await http<Language[]>({
            method: APIMethod.get,
            path: "/api/project/" + project.id + "/languages",
        })

        if (result.value) {
            setLanguages(result.value)
        }
    }

    useEffect(() => {
        load()
    }, [])

    return (
        <>
            <Button onClick={() => setShowDialog(true)} className="mb-3" >Add language</Button>
            <ListGroup>
                {languages && languages.map((language) =>
                    <LanguageListItem
                        language={language}
                        project_id={project.id}
                        onDelete={() => deleteLanguage(language)}
                        key={language.code}
                    />)}
            </ListGroup>
            <AddLaguagePage
                show={showDialog}
                project_id={project.id}
                onHide={() => setShowDialog(false)}
                onSuccess={load} />
        </>
    )
}

export default LanguagesList