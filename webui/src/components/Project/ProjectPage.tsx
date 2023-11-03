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
                <Tabs>
                    <Tab
                        eventKey="languages"
                        title="Languages"
                    >
                        <LanguagesList project={project} />
                    </Tab>
                    {project.role !== ProjectRole.translator &&
                        <Tab
                            eventKey="tokens"
                            title="Localization keys"
                        >
                            <StringTokensList project={project} />
                        </Tab>
                    }
                    <Tab
                        eventKey="history"
                        title="History"
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
                        onHide={() => setShowImport(false)} />
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