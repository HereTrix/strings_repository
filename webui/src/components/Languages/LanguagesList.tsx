import { FC, useEffect, useState } from "react"
import { Button, Container, ListGroup, Row } from "react-bootstrap"
import AddLaguagePage from "./AddLaguagePage"
import Language from "../model/Language"
import Project, { ProjectRole } from "../model/Project"
import { APIMethod, http } from "../Utils/network"
import OptionalImage from "../UI/OptionalImage"
import ErrorAlert from "../UI/ErrorAlert"
import ConfirmationAlert from "../UI/ConfirmationAlert"

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
            className="d-flex justify-content-between align-items-start"
            key={language.code}>
            <OptionalImage src={`/static/flags/${language.code.toLocaleLowerCase()}.png`} alt={language.code} />
            <label>{language.name}</label>
            <Button
                onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    e.nativeEvent.stopImmediatePropagation()
                    onDelete()
                }}
                className="btn-danger"
            >Delete</Button>
        </ListGroup.Item>
    )
}

const LanguagesList: FC<LanguagesProps> = ({ project }) => {

    const [error, setError] = useState<string>()

    const [languages, setLanguages] = useState<Language[]>()
    const [showDialog, setShowDialog] = useState(false)

    const [deletionItem, setDeletionItem] = useState<Language>()

    const deleteLanguage = async (language: Language) => {
        setDeletionItem(undefined)
        const result = await http({
            method: APIMethod.delete,
            path: "/api/language",
            data: { "project": project.id, "code": language.code }
        })

        if (result.error) {
            setError(result.error)
        } else {
            load()
        }
    }

    const load = async () => {
        const result = await http<Language[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/languages`,
        })

        if (result.value) {
            setLanguages(result.value)
        } else {
            setError(result.error)
        }
    }

    useEffect(() => {
        load()
    }, [])

    return (
        <>
            {project.role !== ProjectRole.translator &&
                < Button onClick={() => setShowDialog(true)} className="my-2" >Add language</Button >
            }
            <ListGroup>
                {languages && languages.map((language) =>
                    <LanguageListItem
                        language={language}
                        project_id={project.id}
                        onDelete={() => setDeletionItem(language)}
                        key={language.code}
                    />)}
            </ListGroup>
            <AddLaguagePage
                show={showDialog}
                project_id={project.id}
                onHide={() => setShowDialog(false)}
                onSuccess={load} />
            {error && <ErrorAlert
                error={error}
                onClose={() => setError(undefined)}
            />}
            {deletionItem && <ConfirmationAlert
                message={`You are going to remove ${deletionItem?.name}`}
                onDismiss={() => setDeletionItem(undefined)}
                onConfirm={() => deleteLanguage(deletionItem)}
            />}
        </>
    )
}

export default LanguagesList