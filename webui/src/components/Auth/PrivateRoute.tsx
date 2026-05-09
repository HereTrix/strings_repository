// Copyright (c) StringsRepository Contributors
// SPDX-License-Identifier: MIT

import { Navigate } from "react-router-dom";
import NavBar from "../shell/NavBar";
import { JSX } from "react";

function RequireAuth({ children }: { children: JSX.Element }) {

    const auth = localStorage.getItem("auth")

    if (!auth) {
        // Redirect them to the /login page, but save the current location they were
        // trying to go to when they were redirected. This allows us to send them
        // along to that page after they login, which is a nicer user experience
        // than dropping them off on the home page.
        return <Navigate to="/login" replace />;
    }

    return (
        <>
            <a href="#main-content" className="visually-hidden-focusable">Skip to main content</a>
            <NavBar />
            <main id="main-content">{children}</main>
        </>
    );
}

export default RequireAuth;