import { FC, useEffect, useState } from "react"
import Project, { ProjectRole } from "../model/Project"
import { ListGroup, ListGroupItem } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import Participant from "../model/Participant"

type ProjectInfoProps = {
    project: Project
}

const ProjectInfo: FC<ProjectInfoProps> = ({ project }) => {

    const [participants, setParticipants] = useState<Participant[]>()

    const loadParticipants = async () => {
        if (project.role == ProjectRole.owner || ProjectRole.admin) {
            const data = await http<Participant[]>({
                method: APIMethod.get,
                path: `/api/project/${project.id}/participants`
            })

            if (data.value) {
                setParticipants(data.value)
            }

        }
    }

    useEffect(() => {
        loadParticipants()
    }, [])

    return (
        <>
            <label>{project.description ? project.description : "No description"}</label>
            {participants &&
                <ListGroup>
                    {participants.map(participant =>
                        <ListGroupItem key={participant.email} className="d-flex justify-content-between align-items-start">
                            <label>Name: {participant.first_name}</label>
                            <label>Last name: {participant.last_name}</label>
                            <label>Email: {participant.email}</label>
                        </ListGroupItem>
                    )}
                </ListGroup>
            }
        </>
    )
}

export default ProjectInfo