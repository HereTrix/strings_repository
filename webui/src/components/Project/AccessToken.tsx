import { Button, Container, Dropdown, Form, ListGroup, ListGroupItem, Modal, Stack } from "react-bootstrap";
import Project from "../model/Project";
import { FC, useEffect, useState } from "react";
import { APIMethod, http } from "../Utils/network";
import ErrorAlert from "../UI/ErrorAlert";

type AccessTokenProps = {
    project: Project
    show: boolean
    onHide: () => void
}

type AccessTokenParams = {
    permission: string
    expiration: string | undefined
}

interface AccessToken {
    token: string
    permission: string
    expiration: string | undefined
}

type AccessTokenItemProps = {
    token: AccessToken
    onDelete: (token: string) => void
}

const AccessTokenItem: FC<AccessTokenItemProps> = ({ token, onDelete }) => {
    return <ListGroupItem>
        <Stack direction="horizontal" gap={3}>

            <Container className="border rounded bg-secondary">
                <label className="text-center text-white my-2">{token.token}</label>
            </Container>
            <label>{token.permission}</label>
            <label>{token.expiration}</label>
            <Button
                className="my-2"
                variant="danger"
                onClick={() => onDelete(token.token)}
            >Delete</Button>
        </Stack>
    </ListGroupItem>
}

type GenerateAccessTokenProps = {
    show: boolean
    onHide: () => void
    onSubmit: (data: AccessTokenParams) => void
}

const GenerateAccessTokenPage: FC<GenerateAccessTokenProps> = ({ show, onHide, onSubmit }) => {

    const permissions = ['write', 'read']
    const [permission, setPermisson] = useState<string>('write')
    const [expiration, setExpiration] = useState<string>()

    return <Modal show={show} onHide={onHide}>
        <Modal.Header closeButton>
            <Modal.Title>Access token generation</Modal.Title>
        </Modal.Header>
        <Modal.Body>
            <Container>
                <label>Expiration date:</label>
                <Form.Control
                    type="date"
                    onChange={(e) => setExpiration(e.target.value)} />
            </Container>
            <Dropdown className="my-2">
                <Dropdown.Toggle variant="success" id="dropdown-basic">
                    {permission}
                </Dropdown.Toggle>
                <Dropdown.Menu>
                    {permissions && permissions.map((elm) =>
                        <Dropdown.Item
                            onClick={() => setPermisson(elm)}
                            key={elm}
                        >{elm}</Dropdown.Item>
                    )}
                </Dropdown.Menu>
            </Dropdown>
            <Button
                onClick={() => onSubmit({ permission: permission, expiration: expiration })}
            >Create</Button>
        </Modal.Body>
    </Modal>
}

const AccessTokenPage: FC<AccessTokenProps> = ({ project, show, onHide }) => {

    const [accessToken, setAccessToken] = useState<AccessToken[]>()
    const [error, setError] = useState<string>()
    const [generate, setGenerate] = useState<boolean>(false)

    const generateAccessToken = async (param: AccessTokenParams) => {
        const data = await http<AccessToken>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/access_token`,
            data: param
        })

        if (data.value) {
            var tokens = accessToken
            if (!tokens) {
                tokens = []
            }
            tokens.push(data.value)
            setAccessToken(tokens)
            setGenerate(false)
        } else {
            setError(data.error)
        }
    }

    const deleteAccessToken = async (token: string) => {
        const data = await http<AccessToken[]>({
            method: APIMethod.delete,
            path: `/api/project/${project.id}/access_token`,
            data: { 'token': token }
        })

        if (data.value) {
            setAccessToken(data.value)
        } else {
            setError(data.error)
        }
    }

    const fetchAccessToken = async () => {
        const data = await http<AccessToken[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/access_token`,
        })

        if (data.value) {
            setAccessToken(data.value)
        } else {
            setError(data.error)
        }

    }

    useEffect(() => {
        fetchAccessToken()
    }, [])

    return (
        <>
            <Modal show={show} onHide={onHide}>
                <Modal.Header closeButton>
                    <Modal.Title>Access tokens</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    {accessToken &&
                        <ListGroup>
                            {accessToken.map((itm) =>
                                <AccessTokenItem
                                    token={itm}
                                    key={itm.token}
                                    onDelete={deleteAccessToken} />
                            )}
                        </ListGroup>
                    }
                    <Button className="my-2" onClick={() => setGenerate(true)}>Generate access token</Button>
                </Modal.Body>
            </Modal>
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
            {generate &&
                <GenerateAccessTokenPage
                    show={generate}
                    onHide={() => setGenerate(false)}
                    onSubmit={generateAccessToken}
                />
            }
        </>
    )
}

export default AccessTokenPage;