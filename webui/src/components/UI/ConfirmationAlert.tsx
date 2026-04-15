import { FC } from "react"
import { Button, Modal } from "react-bootstrap"

type ConfirmationAlertProps = {
    message: string | undefined
    onDismiss?: () => void
    onConfirm: () => void
}

const ConfirmationAlert: FC<ConfirmationAlertProps> = ({ message, onDismiss, onConfirm }) => {
    return (
        <Modal show={!!message} onHide={onDismiss} centered>
            <Modal.Header closeButton>
                <Modal.Title>Confirm deletion</Modal.Title>
            </Modal.Header>
            <Modal.Body>{message}</Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onDismiss}>Cancel</Button>
                <Button variant="danger" onClick={onConfirm}>Delete</Button>
            </Modal.Footer>
        </Modal>
    )
}

export default ConfirmationAlert
