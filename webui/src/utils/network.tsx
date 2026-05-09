// Copyright (c) StringsRepository Contributors
// SPDX-License-Identifier: MIT

import { navigate } from "./navigation"

export enum APIMethod {
    get = "GET",
    post = "POST",
    put = "PUT",
    patch = "PATCH",
    delete = "DELETE"
}

type QueryValue =
    | string
    | number
    | boolean
    | null
    | undefined
    | string[]

export type JSONValue =
    | string
    | number
    | boolean
    | null
    | JSONValue[]
    | { [key: string]: JSONValue }

type JSONPayload = Record<string, JSONValue>

type FormDataValue =
    | string
    | string[]
    | number
    | boolean
    | Blob
    | File

type FormDataPayload = Record<string, FormDataValue>

export type BodyPayload = JSONPayload | FormDataPayload
export type QueryPayload = Record<string, QueryValue>

export type APIRequest = {
    isAuth?: boolean
    method: APIMethod
    path: string
    params?: QueryPayload
    data?: BodyPayload
}

export interface APIResponse<T> {
    value?: T
    error?: string
}

interface File {
    name: string
    content: Blob
}

function authHeaders(isAuth?: boolean): [string, string][] {
    const headers: [string, string][] = []
    if (!isAuth) {
        const token = localStorage.getItem("auth")
        if (token) headers.push(["Authorization", token])
    }
    return headers
}

function buildPath(path: string, params?: Record<string, QueryValue>): string {
    if (!params) return path
    const query = new URLSearchParams()

    Object.entries(params ?? {}).forEach(([key, value]) => {
        if (value == null) return

        if (Array.isArray(value)) {
            value.forEach((v) => query.append(key, v))
        } else {
            query.append(key, String(value))
        }
    })
    const queryString = query.toString()

    return queryString ? `${path}?${queryString}` : path
}

function handleUnauthorized(isAuth?: boolean) {
    if (!isAuth) {
        localStorage.removeItem("auth")
        navigate("/login", { replace: true })
    }
}

function handleTwoFARequired() {
    navigate("/2fa-required", { replace: true })
}

function handleTwoFALoginRequired() {
    navigate("/2fa-login", { replace: true })
}

async function extractError(response: Response): Promise<string> {
    try {
        const json = await response.json()
        return json["error"] ?? `Request failed (${response.status})`
    } catch {
        return `Request failed (${response.status})`
    }
}

export async function http<T>(request: APIRequest): Promise<APIResponse<T>> {
    const headers: [string, string][] = [
        ["Content-Type", "application/json"],
        ...authHeaders(request.isAuth),
    ]

    const body = request.data ? JSON.stringify(request.data) : null
    const path = buildPath(request.path, request.params)

    let response: Response
    try {
        response = await fetch(path, { method: request.method, headers, body })
    } catch {
        return { error: "Network error — check your connection." }
    }

    if (response.status === 401) {
        handleUnauthorized(request.isAuth)
        return { error: "Not authorized" }
    }

    if (response.status === 204) {
        return {}
    }

    try {
        const json = await response.json()
        if (response.status === 403 && json["code"] === "2fa_login_required") {
            handleTwoFALoginRequired()
            return { error: json["error"] }
        }
        if (response.status === 403 && json["code"] === "2fa_required") {
            handleTwoFARequired()
            return { error: json["error"] }
        }
        if (!response.ok) {
            return { error: json["error"] ?? `Request failed (${response.status})` }
        }
        return { value: json as T }
    } catch {
        return { error: "Invalid response from server" }
    }
}

export async function upload<T>(request: APIRequest): Promise<APIResponse<T>> {
    const formData = new FormData()
    for (const [key, value] of Object.entries(request.data ?? {})) {
        formData.append(key, String(value));
    }

    const headers = authHeaders(request.isAuth)

    let response: Response
    try {
        response = await fetch(request.path, { method: request.method, headers, body: formData })
    } catch {
        return { error: "Network error — check your connection." }
    }

    if (response.status === 401) {
        handleUnauthorized(request.isAuth)
        return { error: "Not authorized" }
    }

    if (response.status === 204) {
        return {}
    }

    try {
        const json = await response.json()
        if (response.status === 403 && json["code"] === "2fa_login_required") {
            handleTwoFALoginRequired()
            return { error: json["error"] }
        }
        if (response.status === 403 && json["code"] === "2fa_required") {
            handleTwoFARequired()
            return { error: json["error"] }
        }
        if (!response.ok) {
            return { error: json["error"] ?? `Request failed (${response.status})` }
        }
        return { value: json as T }
    } catch {
        return { error: "Invalid response from server" }
    }
}

export async function download(request: APIRequest): Promise<APIResponse<File>> {
    const headers: [string, string][] = [
        ["Content-Type", "application/json"],
        ...authHeaders(request.isAuth),
    ]

    const body = request.data ? JSON.stringify(request.data) : null
    const path = buildPath(request.path, request.params)

    let response: Response
    try {
        response = await fetch(path, { method: request.method, headers, body })
    } catch {
        return { error: "Network error — check your connection." }
    }

    if (response.status === 401) {
        handleUnauthorized(request.isAuth)
        return { error: "Not authorized" }
    }

    if (!response.ok) {
        return { error: await extractError(response) }
    }

    const blob = await response.blob()
    const disposition = response.headers.get("content-disposition")
    const filename = disposition
        ? disposition.split("filename=")[1]?.replace(/"/g, "").trim() ?? ""
        : ""

    return { value: { content: blob, name: filename } }
}
