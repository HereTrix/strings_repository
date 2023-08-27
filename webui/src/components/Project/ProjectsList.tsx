import { FC, useEffect, useState } from "react";
import { Container, ListGroup, Tabs, Tab, Button } from "react-bootstrap";
import { http, APIMethod } from "../Utils/network";
import AddProjectPage from "./AddProjectPage";

type BaseProject = {
    id: number,
    name: string,
    description: string | null
}

interface ProjectProps {
    project: BaseProject,
}

const ProjectListItem: FC<ProjectProps> = ({ project }): JSX.Element => {
    return <ListGroup.Item href={`/project/${project.id}`} action>{project.name}</ListGroup.Item>
}

const AllProjects = () => {

    const [projects, setProjects] = useState<BaseProject[]>([])
    const [showDialog, setShowDialog] = useState(false)

    const fetch = async () => {

        const data = await http<BaseProject[]>({
            method: APIMethod.get,
            path: "/api/projects/list"
        })

        if (data.value) {
            setProjects(data.value)
        } else {

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
                        {projects.map(project => <ProjectListItem project={project} key={project.id} />)}
                    </ListGroup >
                </Tab>
            </Tabs>
            <AddProjectPage
                show={showDialog}
                onHide={() => setShowDialog(false)}
                onSuccess={() => fetch()} />
        </Container>
    )
}

export default AllProjects;