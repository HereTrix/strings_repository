import { FC, JSX, useEffect, useState } from "react";
import { Container, ListGroup, Tabs, Tab, Button, Stack, Modal } from "react-bootstrap";
import { http, APIMethod } from "../Utils/network";
import AddProjectPage from "./AddProjectPage";
import ErrorAlert from "../UI/ErrorAlert";
import ConfirmationAlert from "../UI/ConfirmationAlert";
import { log } from "console";

type BaseProject = {
    id: number,
    name: string,
    description: string | null
    role: string
}

interface ProjectProps {
    project: BaseProject,
    onDelete: () => void
}

const ProjectListItem: FC<ProjectProps> = ({ project, onDelete }): JSX.Element => {
    return <ListGroup.Item
        href={`/project/${project.id}`}
        action
    >
        <Stack direction="horizontal">
            {project.name}
            {(project.role === 'admin' || project.role === 'owner') &&
                <Button
                    className="ms-auto btn-danger"
                    onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        onDelete()
                    }}
                >Delete</Button>
            }
        </Stack>
    </ListGroup.Item>
}

const AllProjects = () => {

    const [error, setError] = useState<string>()
    const [projects, setProjects] = useState<BaseProject[]>([])
    const [showDialog, setShowDialog] = useState(false)
    const [deleteDialog, setDeleteDialog] = useState<BaseProject>()

    const fetch = async () => {

        const data = await http<BaseProject[]>({
            method: APIMethod.get,
            path: "/api/projects/list"
        })

        if (data.value) {
            setProjects(data.value)
        } else {
            setError(data.error)
        }
    }

    const deleteProject = async (project: BaseProject) => {
        const data = await http<BaseProject[]>({
            method: APIMethod.delete,
            path: `/api/project/${project.id}`
        })

        if (data.value) {
            setDeleteDialog(undefined)
            fetch()
        } else {
            setError(data.error)
        }
    }

    useEffect(() => {
        fetch()
    }, [])

    return (
        <Container>
            <Button className="mb-3" onClick={() => setShowDialog(true)}>Add project</Button>
            <Tabs
                defaultActiveKey="projects">
                <Tab
                    eventKey="projects"
                    title="All projects">
                    {projects.length === 0 && <p>No projects yet</p>}
                    <ListGroup>
                        {projects.map(project => <ProjectListItem
                            project={project}
                            key={project.id}
                            onDelete={() => setDeleteDialog(project)} />)}
                    </ListGroup >
                </Tab>
            </Tabs>
            <AddProjectPage
                show={showDialog}
                onHide={() => setShowDialog(false)}
                onSuccess={() => fetch()} />
            {deleteDialog &&
                <ConfirmationAlert
                    message={`Do you want to delete ${deleteDialog.name}?`}
                    onDismiss={() => setDeleteDialog(undefined)}
                    onConfirm={() => deleteProject(deleteDialog)}
                />
            }
            <ErrorAlert
                error={error}
                onClose={() => setError(undefined)} />
        </Container>
    )
}

export default AllProjects;