import { useEffect, useState } from "react"
import { Button, Container, OverlayTrigger, Popover, PopoverBody, Stack, Tab, Tabs } from "react-bootstrap"
import { useParams } from "react-router-dom"
import { history } from "../Utils/history"
import { APIMethod, http } from "../Utils/network"
import Project from "../model/Project"
import ErrorAlert from "../UI/ErrorAlert"
import ExportPage from "./ExportPage"
import OptionalImage from "../UI/OptionalImage"
import TranslationPage from "./TranslationPage"
import HelpPopover from "../UI/HelpPopover"

const LanguageTranslationsPage = () => {

    const [activeTab, setActiveTab] = useState('all')

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
        history.navigate(`/project/${project_id}`, { replace: true })
    }

    const onExport = () => {
        setShowExport(true)
    }

    const activateTab = (tab: string | null) => {
        if (tab) {
            setActiveTab(tab)
        }
    }

    return (
        <Container>
            <Container className="d-flex justify-content-between align-items-start">
                <Button onClick={backToProject}>Back to project</Button>
                {project && <Button onClick={onExport}>Export</Button>}
            </Container>
            <Stack direction="horizontal" gap={1} className="my-1">
                {code && <OptionalImage src={`/static/flags/${code.toLocaleLowerCase()}.png`} alt={code} />}
                <label>This is translation for {code}</label>
                <OverlayTrigger
                    trigger="click"
                    placement="left"
                    overlay={HelpPopover}
                >
                    <Button className="ms-auto" variant="outline-primary">
                        i
                    </Button>
                </OverlayTrigger>
            </Stack>
            {project_id && code &&
                <TranslationPage
                    untranslated={false}
                    project_id={project_id}
                    code={code}
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