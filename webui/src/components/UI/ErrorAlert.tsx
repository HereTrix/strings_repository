import { FC, useState } from "react"
import { Toast, ToastContainer } from "react-bootstrap"

type ErrorAlertProps = {
    error: string | undefined
    onClose: () => void
}

const ErrorAlert: FC<ErrorAlertProps> = ({ error, onClose }) => {
    return (
        <ToastContainer className="p-3" position="middle-center">
            <Toast show={error ? true : false} onClose={onClose} delay={5000} autohide>
                <Toast.Header>
                    <strong className="me-auto error">Error</strong>
                </Toast.Header>
                <Toast.Body>{error}</Toast.Body>
            </Toast>
        </ToastContainer>
    )
}

export default ErrorAlert