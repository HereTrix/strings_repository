import React, { useEffect, useState, Suspense } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { APIMethod, http } from "../../utils/network"
import { Button, Container, Spinner, Stack, Tab, Tabs } from "react-bootstrap"
import Project, { ProjectRole } from "../../types/Project"
import ProjectInfo from "./ProjectInfo"
import LanguagesList from "../Languages/LanguagesList"
import StringTokensList from "../StringTokens/StringTokensList"
import ExportPage from "../Translation/ExportPage"
import HistoryPage from "../History/HistoryPage"
import ImportPage from "../Translation/ImportPage"
import BundlesPage from "../Bundles/BundlesPage"
import ScopeManager from "../StringTokens/ScopeManager"

const VerificationPage = React.lazy(() => import('../Verification/VerificationPage'))

const ProjectPage = () => {

    const { id, tab } = useParams()
    const navigate = useNavigate()
    const allowedTabs = ['languages', 'tokens', 'scopes', 'history', 'bundles', 'info', 'verify']
    const getValidTab = (t: string | undefined | null) =>
        t && allowedTabs.includes(t) ? t : 'languages'
    const [activeTab, setActiveTab] = useState(getValidTab(tab))

    const [error, setError] = useState<string | null>()
    const [project, setProject] = useState<Project>()
    const [showExport, setShowExport] = useState(false)
    const [showImport, setShowImport] = useState(false)

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
            navigate(`/project/${id}/${tab}`)
        }
    }

    useEffect(() => {
        fetch()
    }, [id])

    useEffect(() => {
        setActiveTab(getValidTab(tab))
    }, [tab])

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
                    {(project.role === ProjectRole.owner || project.role === ProjectRole.admin) &&
                        <Tab
                            eventKey="scopes"
                            title="Scopes"
                            key="scopes"
                        >
                            {activeTab === "scopes" && <ScopeManager project={project} />}
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
                        eventKey="bundles"
                        title="Bundles"
                        key="bundles"
                    >
                        {activeTab === "bundles" && <BundlesPage project={project} />}
                    </Tab>
                    <Tab
                        eventKey="info"
                        title="info"
                    >
                        <ProjectInfo project={project} onProviderChange={fetch} />
                    </Tab>
                    {project.has_ai_provider && (
                        <Tab eventKey="verify" title="Verify" key="verify">
                            {activeTab === 'verify' && (
                                <Suspense fallback={<Spinner size="sm" />}>
                                    <VerificationPage project={project} />
                                </Suspense>
                            )}
                        </Tab>
                    )}
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