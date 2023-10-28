import { Button, Container } from "react-bootstrap"
import { useNavigate } from "react-router-dom"
import { APIMethod, http } from "./Utils/network"

const LogoutButton = () => {

    const navigate = useNavigate()

    const logout = async () => {
        const result = await http({
            method: APIMethod.post,
            path: "/api/logout"
        })

        localStorage.removeItem("auth")
        navigate("/login", { replace: true })
    }

    return (
        <Container onClick={logout} className="bg-primary rounded text-white p-2">
            Logout
        </Container>
    )
}

export default LogoutButton;