import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { APIMethod, http } from "../Utils/network"
import { Button, Container, Stack, Tab, Tabs } from "react-bootstrap"
import Project, { ProjectRole } from "../model/Project"
import ProjectInfo from "./ProjectInfo"
import LanguagesList from "../Languages/LanguagesList"
import StringTokensList from "../StringTokens/StringTokensList"
import ExportPage from "../Translation/ExportPage"
import HistoryPage from "../History/HistoryPage"
import ImportPage from "../Translation/ImportPage"

const ProjectPage = () => {

    const [activeTab, setActiveTab] = useState('languages')

    const [error, setError] = useState<string | null>()
    const [project, setProject] = useState<Project>()
    const [showExport, setShowExport] = useState(false)
    const [showImport, setShowImport] = useState(false)

    const { id } = useParams()

    const fetch = async () => {

        const data = await http<Project>({
            method: APIMethod.get,
            path: "/api/project/" + id
        })

        if (data.value) {
            setProject(data.value)
        } else {
            setError(data.error)
        }
    }

    const activateTab = (tab: string | null) => {
        if (tab) {
            setActiveTab(tab)
        }
    }

    useEffect(() => {
        fetch()
    }, [])

    return (
        <Container>
            {project && <>
                <Stack direction="horizontal" gap={3}>
                    <h1>{project.name}</h1>
                    <Button
                        className="ms-auto"
                        onClick={() => setShowImport(true)}
                    >Import</Button>
                    <Button
                        className="mx-2"
                        onClick={() => setShowExport(true)}
                    >Export</Button>
                </Stack>
                <Tabs activeKey={activeTab} onSelect={(e) => activateTab(e)}>
                    <Tab
                        eventKey="languages"
                        title="Languages"
                        key="Languages"
                    >
                        <LanguagesList project={project} />
                    </Tab>
                    {project.role !== ProjectRole.translator &&
                        <Tab
                            eventKey="tokens"
                            title="Localization keys"
                            key="tokens"
                        >
                            {activeTab === "tokens" && <StringTokensList project={project} />}
                        </Tab>
                    }
                    <Tab
                        eventKey="history"
                        title="History"
                        key="history"
                    >
                        <HistoryPage project={project} />
                    </Tab>
                    <Tab
                        eventKey="info"
                        title="info"
                    >
                        <ProjectInfo project={project} />
                    </Tab>
                </Tabs>
                {showImport &&
                    <ImportPage
                        project={project}
                        show={showImport}
                        onHide={() => {
                            setShowImport(false)
                            setProject(undefined)
                            fetch()
                        }} />
                }
                {showExport &&
                    <ExportPage
                        project={project}
                        show={showExport}
                        onHide={() => setShowExport(false)} />
                }
            </>}
        </Container >
    )
}

export default ProjectPage