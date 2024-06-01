import { FC, useEffect, useState } from "react"
import Project, { ProjectRole } from "../model/Project"
import { Button, Col, Container, Dropdown, ListGroup, ListGroupItem, Row, Stack } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import Participant from "../model/Participant"
import InviteUserPage from "./InviteUserPage"
import AccessTokenPage from "./AccessToken"
import ErrorAlert from "../UI/ErrorAlert"

type ProjectInfoProps = {
    project: Project
}

type ParticipantItemProps = {

}

const ProjectInfo: FC<ProjectInfoProps> = ({ project }) => {

    const [error, setError] = useState<string>()
    const [participants, setParticipants] = useState<Participant[]>()
    const [inviteUser, setInviteUser] = useState<boolean>(false)
    const [accessToken, setAccessToken] = useState<boolean>(false)
    const [roles, setRoles] = useState<string[]>([])

    const loadParticipants = async () => {
        const data = await http<Participant[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/participants`
        })

        if (data.value) {
            setParticipants(data.value)
        } else {
            setError(data.error)
        }
    }

    const loadRoles = async () => {
        const data = await http<string[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/roles`
        })

        if (data.value) {
            setRoles(data.value)
        } else {
            setError(data.error)
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
        } else {
            setError(data.error)
        }
    }

    const removeParticipant = async (participant_id: string) => {
        const data = await http<Participant[]>({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/participants`,
            data: { 'user_id': participant_id }
        })

        if (data.value) {
            setParticipants(data.value)
        } else {
            setError(data.error)
        }
    }

    useEffect(() => {
        if (project.role !== ProjectRole.editor) {
            loadParticipants()
        }
        loadRoles()
    }, [])

    return (
        <>
            {roles.length > 0 &&
                <Container className="align-content-right" fluid>
                    <Stack direction="horizontal" gap={3} className="my-2">
                        <Button
                            onClick={() => setInviteUser(true)}>Invite user</Button>
                        <Button
                            onClick={() => setAccessToken(true)}>Access token</Button>
                    </Stack>
                </Container>
            }
            <label>{project.description ? project.description : "No description"}</label>
            {participants &&
                <ListGroup>
                    {participants.map(participant =>
                        <ListGroupItem
                            key={participant.email}
                            className="d-flex justify-content-between"
                        >
                            <Col className="mx-2">
                                <label>Name: {participant.first_name}</label>
                            </Col>
                            <Col className="mx-2">
                                <label>Last name: {participant.last_name}</label>
                            </Col>
                            <Col className="mx-2">
                                <label>Email: {participant.email}</label>
                            </Col>
                            <Col className="mx-2">
                                <Stack direction="horizontal" gap={2}>
                                    <label>Role: </label>
                                    {participant.can_edit
                                        ? <Dropdown>
                                            <Dropdown.Toggle variant="success" id="dropdown-basic">
                                                {participant.role}
                                            </Dropdown.Toggle>
                                            <Dropdown.Menu>
                                                {roles && roles.map((role) =>
                                                    <Dropdown.Item onClick={() => updateRole(participant.id, role)} key={role}>{role}</Dropdown.Item>
                                                )}
                                            </Dropdown.Menu>
                                        </Dropdown>
                                        : <label>{participant.role}</label>}
                                </Stack>
                            </Col>
                            {participant.can_edit &&
                                <Button
                                    className="btn-danger"
                                    onClick={() => removeParticipant(participant.id)}
                                >
                                    Delete
                                </Button>
                            }
                        </ListGroupItem>
                    )}
                </ListGroup >
            }
            {inviteUser &&
                <InviteUserPage
                    projectId={project.id}
                    roles={roles}
                    show={inviteUser}
                    onHide={() => setInviteUser(false)}
                    onSuccess={() => loadParticipants()}
                />
            }
            {accessToken &&
                <AccessTokenPage
                    project={project}
                    show={accessToken}
                    onHide={() => setAccessToken(false)}
                />
            }
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </>
    )
}

export default ProjectInfo