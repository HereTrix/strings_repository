import { Button } from "react-bootstrap"
import { useNavigate } from "react-router-dom"
import { APIMethod, http } from "./Utils/network"

const LogoutButton = () => {

    const navigate = useNavigate()

    const logout = async () => {
        const result = await http({
            method: APIMethod.post,
            path: "api/logout"
        })

        localStorage.removeItem("auth")
        navigate("/login", { replace: true })
    }

    return (
        <Button onClick={logout}>
            Logout
        </Button>
    )
}

export default LogoutButton;