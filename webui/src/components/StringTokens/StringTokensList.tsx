import { FC, useEffect, useState } from "react"
import StringToken from "../model/StringToken"
import Project from "../model/Project"
import { Button, ListGroup } from "react-bootstrap"
import { APIMethod, http } from "../Utils/network"
import AddTokenPage from "./AddTokenPage"

type StringTokenProps = {
    project: Project
}

type StringTokenItemProps = {
    token: StringToken,
    onDelete: () => void
}

const StringTokenListItem: FC<StringTokenItemProps> = ({ token, onDelete }) => {

    return (
        <ListGroup.Item
            className="d-flex justify-content-between align-items-start">
            <label>{token.token}</label>
            <Button onClick={onDelete}>Delete</Button>
        </ListGroup.Item>
    )
}

const StringTokensList: FC<StringTokenProps> = ({ project }) => {

    const [showDialog, setShowDialog] = useState(false)
    const [tokens, setTokens] = useState<StringToken[]>()

    const fetch = async () => {
        const result = await http<StringToken[]>({
            method: APIMethod.get,
            path: "/api/project/" + project.id + "/tokens"
        })

        if (result.value) {
            setTokens(result.value)
        }
    }

    const deleteToken = async (token: StringToken) => {
        const result = await http({
            method: APIMethod.delete,
            path: "/api/string_token",
            data: { "id": token.id }
        })

        if (result.error) {

        } else {
            console.log('fetch')
            fetch()
        }
    }

    useEffect(() => {
        fetch()
    }, [])

    return (
        <>
            <Button onClick={() => setShowDialog(true)} className="mb-3" >Add localization key</Button>
            <ListGroup>
                {tokens && tokens.map((token) =>
                    <StringTokenListItem
                        key={token.id}
                        token={token}
                        onDelete={() => deleteToken(token)} />
                )}
            </ListGroup>
            <AddTokenPage
                project_id={project.id}
                show={showDialog}
                onHide={() => setShowDialog(false)}
                onSuccess={fetch} />
        </>
    )
}

export default StringTokensList