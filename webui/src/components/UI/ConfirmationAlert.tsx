import { FC } from "react"
import { Button, Stack, Toast, ToastContainer } from "react-bootstrap"

type ConfirmationAlertProps = {
    message: string | undefined
    onDismiss?: () => void
    onConfirm: () => void
}

const ConfirmationAlert: FC<ConfirmationAlertProps> = ({ message, onDismiss, onConfirm }) => {
    return (
        <ToastContainer className="p-3" position="middle-center">
            <Toast show={message ? true : false} onClose={onDismiss} delay={5000}>
                <Toast.Header>
                    <strong className="me-auto error">Warning</strong>
                </Toast.Header>
                <Toast.Body>
                    <Stack direction="vertical" className="gap-3">
                        {message}
                        <Stack direction="horizontal">
                            <Button
                                onClick={onDismiss}
                            >Decline
                            </Button>
                            <Button
                                className="btn-danger ms-auto"
                                onClick={onConfirm}
                            >Delete
                            </Button>
                        </Stack>
                    </Stack>
                </Toast.Body>
            </Toast>
        </ToastContainer>
    )
}

export default ConfirmationAlert