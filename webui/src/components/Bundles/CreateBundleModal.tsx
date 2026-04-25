import { FC, JSX, useState } from "react"
import { Button, Form, Modal } from "react-bootstrap"
import { APIMethod, http } from "../../utils/network"
import { Bundle } from "../../types/Bundle"
import Project from "../../types/Project"

type CreateBundleModalProps = {
    project: Project
    show: boolean
    onHide: () => void
    onCreated: (bundle: Bundle) => void
}

const CreateBundleModal: FC<CreateBundleModalProps> = ({ project, show, onHide, onCreated }): JSX.Element => {
    const [versionName, setVersionName] = useState("")
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | undefined>()

    const onCreate = async () => {
        setLoading(true)
        setError(undefined)

        const result = await http<Bundle>({
            method: APIMethod.post,
            path: `/api/project/${project.id}/bundles`,
            data: versionName.trim() ? { version_name: versionName.trim() } : {},
        })

        setLoading(false)

        if (result.value) {
            onCreated(result.value)
        } else {
            setError(result.error)
        }
    }

    return (
        <Modal show={show} onHide={onHide}>
            <Modal.Header closeButton>
                <Modal.Title>Create bundle</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form.Group>
                    <Form.Label>Version name</Form.Label>
                    <Form.Control
                        type="text"
                        placeholder="Leave empty to auto-generate (v1, v2, …)"
                        value={versionName}
                        onChange={(e) => setVersionName(e.target.value)}
                    />
                    <Form.Text className="text-muted">
                        Reserved names: <code>active</code>, <code>live</code>
                    </Form.Text>
                </Form.Group>
                {error && <p className="text-danger mt-2">{error}</p>}
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide}>Cancel</Button>
                <Button onClick={onCreate} disabled={loading}>
                    {loading ? "Creating…" : "Create snapshot"}
                </Button>
            </Modal.Footer>
        </Modal>
    )
}

export default CreateBundleModal
