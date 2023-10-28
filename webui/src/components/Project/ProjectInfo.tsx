import { FC, useEffect, useState } from "react"
import Project, { ProjectRole } from "../model/Project"
import { Button, Col, Dropdown, ListGroup, ListGroupItem, Row, Stack } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import Participant from "../model/Participant"
import InviteUserPage from "./InviteUserPage"

type ProjectInfoProps = {
    project: Project
}

const ProjectInfo: FC<ProjectInfoProps> = ({ project }) => {

    const [participants, setParticipants] = useState<Participant[]>()
    const [inviteUser, setInviteUser] = useState<boolean>(false)
    const [roles, setRoles] = useState<string[]>([])

    const loadParticipants = async () => {
        const data = await http<Participant[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/participants`
        })

        if (data.value) {
            setParticipants(data.value)
        }
    }

    const loadRoles = async () => {
        const data = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/roles`
        })

        if (data.value) {
            setRoles(data.value)
        }
    }

    const updateRole = async (participant_id: string, role: string) => {
        const data = await http<Participant[]>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/participants`,
            data: { 'user_id': participant_id, 'role': role }
        })

        if (data.value) {
            setParticipants(data.value)
        }
    }

    useEffect(() => {
        loadParticipants()
        loadRoles()
    }, [])

    return (
        <>
            {roles.length > 0 &&
                <Row className="my-2">
                    <Col>
                        <Button
                            onClick={() => setInviteUser(true)}>Invite user</Button>
                    </Col>
                </Row>
            }
            <label>{project.description ? project.description : "No description"}</label>
            {participants &&
                <ListGroup>
                    {participants.map(participant =>
                        <ListGroupItem key={participant.email} className="d-flex">
                            <Stack direction="horizontal" gap={5} className="justify-content-between align-items-end">

                                <Row className="p-2">
                                    <label>Name: {participant.first_name}</label>
                                </Row>
                                <Row className="p-2">
                                    <label>Last name: {participant.last_name}</label>
                                </Row>
                                <Row className="p-2">
                                    <label>Email: {participant.email}</label>
                                </Row>
                                <Stack direction="horizontal" gap={2}>
                                    <label>Role: </label>
                                    {participant.can_edit
                                        ? <Dropdown>
                                            <Dropdown.Toggle variant="success" id="dropdown-basic">
                                                {participant.role}
                                            </Dropdown.Toggle>
                                            <Dropdown.Menu>
                                                {roles && roles.map((role) =>
                                                    <Dropdown.Item onClick={() => updateRole(participant.id, role)}>{role}</Dropdown.Item>
                                                )}
                                            </Dropdown.Menu>
                                        </Dropdown>
                                        : <label>{participant.role}</label>}
                                </Stack>
                            </Stack>
                        </ListGroupItem>
                    )}
                </ListGroup >
            }
            {
                inviteUser &&
                <InviteUserPage
                    projectId={project.id}
                    roles={roles}
                    show={inviteUser}
                    onHide={() => setInviteUser(false)}
                    onSuccess={() => loadParticipants()}
                />
            }
        </>
    )
}

export default ProjectInfo