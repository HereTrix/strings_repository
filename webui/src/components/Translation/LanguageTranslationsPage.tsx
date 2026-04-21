import { useEffect, useState } from "react"
import { Button, Container, ProgressBar, Stack } from "react-bootstrap"
import { useNavigate, useParams } from "react-router-dom"
import { APIMethod, http } from "../Utils/network"
import Project from "../model/Project"
import { LanguageProgress } from "../model/Language"
import ErrorAlert from "../UI/ErrorAlert"
import ExportPage from "./ExportPage"
import OptionalImage from "../UI/OptionalImage"
import TranslationPage from "./TranslationPage"

const LanguageTranslationsPage = () => {
    const navigate = useNavigate()

    const { project_id, code } = useParams()
    const [showExport, setShowExport] = useState(false)

    const [project, setProject] = useState<Project>()
    const [progress, setProgress] = useState<LanguageProgress>()

    const [error, setError] = useState<string>()

    useEffect(() => {
        fetchProject()
        fetchProgress()
    }, [])

    const fetchProgress = async () => {
        const data = await http<Record<string, LanguageProgress>>({
            method: APIMethod.get,
            path: `/api/project/${project_id}/progress`,
        })
        if (data.value && code) {
            setProgress(data.value[code.toUpperCase()])
        }
    }

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
            <Container className="d-flex my-3 justify-content-between align-items-center">
                <Button onClick={backToProject}>Back to project</Button>
                <Stack direction="vertical" gap={2} className="align-items-center">
                    <Stack direction="horizontal" gap={2} className="my-1 align-items-center justify-content-center">
                        {language && <OptionalImage src={language.img} alt={code ?? ""} width={32} height={24} />}
                        <label>This is translation for {code}</label>
                    </Stack>
                    {progress && (
                        <ProgressBar
                            now={progress.percent}
                            label={`${progress.percent}%`}
                            style={{ width: '200px' }}
                            variant={progress.percent >= 80 ? 'success' : progress.percent >= 40 ? 'warning' : 'danger'}
                        />
                    )}
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