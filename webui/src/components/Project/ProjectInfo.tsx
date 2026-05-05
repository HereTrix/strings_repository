import { FC, useEffect, useState } from "react"
import Project, { ProjectRole } from "../../types/Project"
import { Button, Col, Dropdown, Form, ListGroup, ListGroupItem, Stack } from "react-bootstrap"
import { APIMethod, http } from "../../utils/network"
import Participant from "../../types/Participant"
import InviteUserPage from "./InviteUserPage"
import AccessTokenPage from "./AccessToken"
import IntegrationSettings from "./IntegrationSettings"
import WebhookSettings from "./WebhookSettings"
import CollapseSection from "../UI/CollapseSection"
import ErrorAlert from "../UI/ErrorAlert"

type ProjectInfoProps = {
    project: Project
}

const ProjectInfo: FC<ProjectInfoProps> = ({ project }) => {

    const [error, setError] = useState<string>()
    const [participants, setParticipants] = useState<Participant[]>()
    const [inviteUser, setInviteUser] = useState<boolean>(false)
    const [accessToken, setAccessToken] = useState<boolean>(false)
    const [roles, setRoles] = useState<string[]>([])
    const [require2fa, setRequire2fa] = useState(project.require_2fa)

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
                <Stack direction="horizontal" gap={3} className="my-2">
                    <Button onClick={() => setInviteUser(true)}>Invite user</Button>
                    <Button onClick={() => setAccessToken(true)}>Access token</Button>
                </Stack>
            }

            <label>{project.description ? project.description : "No description"}</label>

            <CollapseSection title="Translation Integration">
                <IntegrationSettings project={project} />
            </CollapseSection>

            <CollapseSection title="Webhooks">
                <WebhookSettings project={project} />
            </CollapseSection>

            {project.role === ProjectRole.owner && (
                <CollapseSection title="Security Settings">
                    <Form.Check
                        type="switch"
                        id="require-2fa-toggle"
                        label="Require 2FA for all project members"
                        checked={require2fa}
                        onChange={async (e) => {
                            const newValue = e.target.checked
                            const result = await http({
                                method: APIMethod.patch,
                                path: `/api/project/${project.id}`,
                                data: { require_2fa: newValue }
                            })
                            if (result.error) {
                                setError(result.error)
                            } else {
                                setRequire2fa(newValue)
                            }
                        }}
                    />
                    <Form.Text className="text-muted">
                        When enabled, all project members must have 2FA active to access this project.
                    </Form.Text>
                </CollapseSection>
            )}

            <CollapseSection title="Participants">
                {participants &&
                    <ListGroup>
                        {participants.map(participant =>
                            <ListGroupItem
                                key={participant.id}
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
                    </ListGroup>
                }
            </CollapseSection>

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
