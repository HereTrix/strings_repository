import { useEffect, useState } from "react"
import { Button, ButtonGroup, Container, ProgressBar, Stack } from "react-bootstrap"
import { useNavigate, useParams } from "react-router-dom"
import { APIMethod, http } from "../../utils/network"
import Project from "../../types/Project"
import { LanguageProgress } from "../../types/Language"
import Scope from "../../types/Scope"
import ErrorAlert from "../UI/ErrorAlert"
import ExportPage from "./ExportPage"
import OptionalImage from "../UI/OptionalImage"
import TranslationPage from "./TranslationPage"
import ScopesGallery from "../StringTokens/ScopesGallery"

const LanguageTranslationsPage = () => {
    const navigate = useNavigate()

    const { project_id, code } = useParams()
    const [showExport, setShowExport] = useState(false)

    const [project, setProject] = useState<Project>()
    const [progress, setProgress] = useState<LanguageProgress>()
    const [viewMode, setViewMode] = useState<'all' | 'scopes'>('all')
    const [selectedScope, setSelectedScope] = useState<Scope>()

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

    const switchToAll = () => {
        setViewMode('all')
        setSelectedScope(undefined)
    }

    const switchToScopes = () => {
        setViewMode('scopes')
        setSelectedScope(undefined)
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
                    <ButtonGroup size="sm">
                        <Button
                            variant={viewMode === 'all' ? 'primary' : 'outline-primary'}
                            onClick={switchToAll}
                        >
                            All
                        </Button>
                        <Button
                            variant={viewMode === 'scopes' ? 'primary' : 'outline-primary'}
                            onClick={switchToScopes}
                        >
                            By Scope
                        </Button>
                    </ButtonGroup>
                </Stack>
                {project && <Button onClick={onExport}>Export</Button>}
            </Container>

            {viewMode === 'scopes' && selectedScope && (
                <Button
                    variant="outline-secondary"
                    size="sm"
                    className="mb-2"
                    onClick={() => setSelectedScope(undefined)}
                >
                    ← Back to scopes
                </Button>
            )}

            {project && <>
                {code && viewMode === 'all' &&
                    <TranslationPage
                        code={code}
                        project={project}
                    />
                }
                {viewMode === 'scopes' && !selectedScope && project_id && (
                    <ScopesGallery
                        project_id={project_id}
                        onScopeSelect={setSelectedScope}
                    />
                )}
                {viewMode === 'scopes' && selectedScope && code && (
                    <TranslationPage
                        code={code}
                        project={project}
                        scopeId={selectedScope.id}
                        scope={selectedScope}
                    />
                )}
            </>
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
