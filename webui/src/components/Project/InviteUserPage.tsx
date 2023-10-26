import { FC, useState } from "react"
import { Button, Container, Dropdown, Modal, Row } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"

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

const InviteUserPage: FC<InviteUserPage> = ({ projectId, roles, show, onHide, onSuccess }) => {

    const [error, setError] = useState<string>()
    const [code, setCode] = useState<string>()
    const [selectedRole, setSelectedRole] = useState<string>()

    const generateCode = async () => {
        const data = await http<Invitation>({
            method: APIMethod.post,
            path: `/api/project/${projectId}/invite`,
            data: { 'role': selectedRole }
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
                {error && <label className="error">{error}</label>}
                {code &&
                    <Container className="my-3">
                        <Row>
                            <label>Please, send this Invitation code to participant</label>
                        </Row>
                        <Row className="border rounded bg-secondary">
                            <label className="text-center text-white my-2">{code}</label>
                        </Row>
                    </Container>
                }
            </Modal.Body>
        </Modal>
    )
}

export default InviteUserPage
