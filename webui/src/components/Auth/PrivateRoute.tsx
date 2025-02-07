import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { history } from "../Utils/history";
import NavBar from "../NavBar";
import { JSX } from "react";

function RequireAuth({ children }: { children: JSX.Element }) {
    // Store hooks to have possibility to navigate outside of component
    if (!history.navigate) {
        history.navigate = useNavigate()
        history.location = useLocation()
    }

    const auth = localStorage.getItem("auth")

    if (!auth) {
        // Redirect them to the /login page, but save the current location they were
        // trying to go to when they were redirected. This allows us to send them
        // along to that page after they login, which is a nicer user experience
        // than dropping them off on the home page.
        return <Navigate to="/login" replace />;
    }

    return <><NavBar />{children}</>;
}

export default RequireAuth;