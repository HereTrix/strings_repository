// Copyright (c) StringsRepository Contributors
// SPDX-License-Identifier: MIT

import { FC, useState } from "react"
import { Button, Container, Dropdown, Modal, Row } from "react-bootstrap"
import { APIMethod, BodyPayload, http } from "../../utils/network"

type InviteUserPage = {
    projectId: number
    roles: string[]
    show: boolean
    onHide: () => void
    onSuccess: () => void
}

type Invitation = {
    code: string
}

const InviteUserPage: FC<InviteUserPage> = ({ projectId, roles, show, onHide }) => {

    const [error, setError] = useState<string>()
    const [code, setCode] = useState<string>()
    const [selectedRole, setSelectedRole] = useState<string | null>(null)

    const payload: BodyPayload = { role: selectedRole }

    const generateCode = async () => {
        const data = await http<Invitation>({
            method: APIMethod.post,
            path: `/api/project/${projectId}/invite`,
            data: payload
        })

        if (data.value) {
            setCode(data.value.code)
        } else {
            setError(data.error)
        }
    }

    return (
        <Modal show={show} onHide={onHide}>
            <Modal.Header closeButton>
                <Modal.Title>Invite user</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Dropdown className="my-2">
                    <Dropdown.Toggle variant="success" id="dropdown-basic">
                        {selectedRole ? selectedRole : "Select role"}
                    </Dropdown.Toggle>
                    <Dropdown.Menu>
                        {roles && roles.map((role) =>
                            <Dropdown.Item onClick={() => setSelectedRole(role)}>{role}</Dropdown.Item>
                        )}
                    </Dropdown.Menu>
                </Dropdown>
                <Button onClick={generateCode}>Generate invitation code</Button>
                {error && <span className="error">{error}</span>}
                {code &&
                    <Container className="my-3">
                        <Row>
                            <span>Please, send this Invitation code to participant</span>
                        </Row>
                        <Row className="border rounded bg-secondary">
                            <span className="text-center text-white my-2">{code}</span>
                        </Row>
                    </Container>
                }
            </Modal.Body>
        </Modal>
    )
}

export default InviteUserPage
