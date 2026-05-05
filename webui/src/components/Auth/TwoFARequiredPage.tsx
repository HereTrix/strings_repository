import { useNavigate } from "react-router-dom"
import { Button, Container } from "react-bootstrap"

const TwoFARequiredPage = () => {
    const navigate = useNavigate()

    return (
        <Container className="d-flex flex-column align-items-center justify-content-center" style={{ minHeight: "60vh" }}>
            <h2>Two-Factor Authentication Required</h2>
            <p className="text-muted mt-2 mb-4">
                This project requires 2FA. Enable two-factor authentication in your profile to access it.
            </p>
            <div className="d-flex gap-3">
                <Button onClick={() => navigate("/profile?expand=2fa")}>
                    Set up 2FA
                </Button>
                <Button variant="outline-secondary" onClick={() => navigate("/")}>
                    Go to Home
                </Button>
            </div>
        </Container>
    )
}

export default TwoFARequiredPage
