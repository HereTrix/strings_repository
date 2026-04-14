import { FC, JSX, useEffect, useState } from "react"
import { Badge, Button, ListGroup, Stack } from "react-bootstrap"
import { useNavigate } from "react-router-dom"
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
    canManage: boolean
    onDelete: () => void
    onSetDefault: () => void
    onNavigate: () => void
}

const LanguageListItem: FC<LanguageListItemProp> = ({ language, project_id, canManage, onDelete, onSetDefault, onNavigate }): JSX.Element => {

    return (
        <ListGroup.Item
            action
            onClick={onNavigate}
            className="d-flex justify-content-between align-items-center"
            key={language.code}>
            <Stack direction="horizontal" gap={2}>
                <OptionalImage src={language.img} alt={language.code} width={50} height={38} />
                <label>{language.name}</label>
                {language.is_default && <Badge bg="primary">Default</Badge>}
            </Stack>
            <Stack direction="horizontal" gap={2}>
                {canManage && !language.is_default && (
                    <Button
                        variant="outline-secondary"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); onSetDefault() }}
                    >Set as default</Button>
                )}
                <Button
                    onClick={(e) => { e.stopPropagation(); onDelete() }}
                    className="btn-danger"
                >Delete</Button>
            </Stack>
        </ListGroup.Item>
    )
}

const LanguagesList: FC<LanguagesProps> = ({ project }) => {

    const navigate = useNavigate()

    const [error, setError] = useState<string>()
    const [languages, setLanguages] = useState<Language[]>()
    const [showDialog, setShowDialog] = useState(false)
    const [deletionItem, setDeletionItem] = useState<Language>()

    const canManage = project.role === ProjectRole.owner || project.role === ProjectRole.admin

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

    const setDefault = async (language: Language) => {
        const result = await http({
            method: APIMethod.put,
            path: `/api/project/${project.id}/language/${language.code}/default`,
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
                <Button onClick={() => setShowDialog(true)} className="my-2">Add language</Button>
            }
            <ListGroup>
                {languages && languages.map((language) =>
                    <LanguageListItem
                        language={language}
                        project_id={project.id}
                        canManage={canManage}
                        onDelete={() => setDeletionItem(language)}
                        onSetDefault={() => setDefault(language)}
                        onNavigate={() => navigate(`/project/${project.id}/language/${language.code.toLowerCase()}`)}
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