import React from "react"
import App from "./components/App"
import { createRoot } from "react-dom/client";

const savedTheme = localStorage.getItem('theme') ?? 'light'
document.documentElement.setAttribute('data-bs-theme', savedTheme)

const root = createRoot(document.getElementById("app") as HTMLElement);
root.render(
    <App />
)