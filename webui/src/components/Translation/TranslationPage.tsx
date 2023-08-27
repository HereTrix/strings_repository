import { ChangeEventHandler, FC, useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { APIMethod, http } from "../Utils/network"
import Translation from "../model/Translation"
import { Button, Container, ListGroup, Row, Stack } from "react-bootstrap"
import { history } from "../Utils/history"
import ExportPage from "./ExportPage"
import Project from "../model/Project"

type TranslationListItemProps = {
    translation: Translation,
    onSave: (translation: Translation) => void
}

const TranslationListItem: FC<TranslationListItemProps> = ({ translation, onSave }) => {

    const [canSave, setCanSave] = useState<boolean>(false)
    const [text, setText] = useState<string | undefined>(translation.translation)

    const onTranslationChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
        setText(event.target.value)
        setCanSave(true)
    }

    const save = () => {
        const newTranslation: Translation = { token: translation.token, translation: text }
        onSave(newTranslation)
    }

    return (
        <ListGroup.Item >
            <Stack>
                <Row>
                    <label>{translation.token}</label>
                </Row>
                <Row>
                    <textarea defaultValue={translation.translation} onChange={onTranslationChange} />
                    {canSave && <Button onClick={save}>Save</Button>}
                </Row>
            </Stack>
        </ListGroup.Item>
    )
}

const TranslationPage = () => {

    const { project_id, code } = useParams()
    const [showExport, setShowExport] = useState(false)

    const [project, setProject] = useState<Project>()
    const [translations, setTranslations] = useState<Translation[]>()

    const fetchProject = async () => {
        const data = await http<Project>({
            method: APIMethod.get,
            path: `/api/project/${project_id}`
        })

        if (data.value) {
            setProject(data.value)
        }
    }

    const fetch = async () => {
        const result = await http<Translation[]>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/translations/${code}`
        })

        if (result.error) {

        } else {
            setTranslations(result.value)
        }
    }

    const saveTranslation = async (translation: Translation) => {
        const result = await http({
            method: APIMethod.post,
            path: "/api/translation",
            data: { "project_id": project_id, "code": code, "token": translation.token, "translation": translation.translation }
        })

        if (result.error) {

        } else {

        }
    }

    const backToProject = () => {
        history.navigate(`/project/${project_id}`, { replace: true })
    }

    const onExport = () => {
        setShowExport(true)
    }

    useEffect(() => {
        fetchProject()
        fetch()
    }, [])

    return (
        <Container>
            <Container className="d-flex justify-content-between align-items-start">
                <Button onClick={backToProject}>Back to project</Button>
                {project && <Button onClick={onExport}>Export</Button>}
            </Container>
            <ListGroup>
                <label>This is translation for {code}</label>
                {translations && translations.map(
                    (translation) => <TranslationListItem
                        translation={translation}
                        onSave={saveTranslation}
                        key={translation.token} />
                )}
            </ListGroup>
            {project &&
                <ExportPage
                    project={project}
                    code={code}
                    show={showExport}
                    onHide={() => setShowExport(false)} />
            }
        </Container>
    )
}

export default TranslationPage