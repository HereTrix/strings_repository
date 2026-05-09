// Copyright (c) StringsRepository Contributors
// SPDX-License-Identifier: MIT

import { Container } from "react-bootstrap"
import { useNavigate } from "react-router-dom"
import { APIMethod, http } from "../../utils/network"

const LogoutButton = () => {

    const navigate = useNavigate()

    const logout = async () => {
        const result = await http({
            method: APIMethod.post,
            path: "/api/logout"
        })

        if (result.error) {
            // Ignore logout error
        }

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