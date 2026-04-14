import { useEffect, useState } from "react"
import { Button, Container, Stack } from "react-bootstrap"
import { useNavigate, useParams } from "react-router-dom"
import { APIMethod, http } from "../Utils/network"
import Project from "../model/Project"
import ErrorAlert from "../UI/ErrorAlert"
import ExportPage from "./ExportPage"
import OptionalImage from "../UI/OptionalImage"
import TranslationPage from "./TranslationPage"

const LanguageTranslationsPage = () => {
    const navigate = useNavigate()

    const { project_id, code } = useParams()
    const [showExport, setShowExport] = useState(false)

    const [project, setProject] = useState<Project>()

    const [error, setError] = useState<string>()

    useEffect(() => {
        fetchProject()
    }, [])

    const fetchProject = async () => {
        const data = await http<Project>({
            method: APIMethod.get,
            path: `/api/project/${project_id}`
        })

        if (data.value) {
            setProject(data.value)
        } else {
            setError(data.error)
        }
    }

    const backToProject = () => {
        navigate(`/project/${project_id}`, { replace: true })
    }

    const onExport = () => {
        setShowExport(true)
    }

    const language = project?.languages.find(l => l.code.toLowerCase() === code?.toLowerCase())
    return (
        <Container>
            <Container className="d-flex my-3 justify-content-between align-items-start">
                <Button onClick={backToProject}>Back to project</Button>
                <Stack direction="horizontal" gap={1} className="my-1">
                    {language && <OptionalImage src={language.img} alt={code ?? ""} width={32} height={24} />}
                    <label>This is translation for {code}</label>
                </Stack>
                {project && <Button onClick={onExport}>Export</Button>}
            </Container>
            {project_id && code &&
                <TranslationPage
                    project_id={project_id}
                    code={code}
                    project={project}
                />
            }
            {project &&
                <ExportPage
                    project={project}
                    code={code}
                    show={showExport}
                    onHide={() => setShowExport(false)} />
            }
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </Container>
    )
}

export default LanguageTranslationsPage