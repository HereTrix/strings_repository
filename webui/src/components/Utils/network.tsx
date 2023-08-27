import { history } from "./history"

export enum APIMethod {
    get = "GET",
    post = "POST",
    put = "PUT",
    delete = "DELETE"
}

export type APIRequest = {
    isAuth?: boolean
    method: APIMethod
    path: string
    params?: any | null
    data?: any | null
}

export interface APIResponse<T> {
    value?: T
    error?: string
}

export async function download(request: APIRequest): Promise<APIResponse<Blob>> {
    var headers: HeadersInit = []
    headers.push(["Content-Type", "application/json"])

    if (!request.isAuth) {
        const token = localStorage.getItem("auth")
        if (token) {
            headers.push(["Authorization", token])
        }
    }

    var path = request.path

    if (request.params) {
        const query = new URLSearchParams(request.params)
        path = path + "?" + query.toString()
    }

    var data: BodyInit | null = null
    if (request.data) {
        data = JSON.stringify(request.data)
    }
    var requestOptions = {
        method: request.method,
        headers: headers,
        body: data
    }
    const response = await fetch(path, requestOptions)
    if (response.status == 401) {
        localStorage.removeItem("auth")
        history.navigate("/login", { replace: true })
        return { error: "Not authorized" }
    } else if (response.status == 200) {
        const blob = await response.blob()
        return { value: blob }
    } else {
        return { error: "Failed to load" }
    }
}

export async function http<T>(request: APIRequest): Promise<APIResponse<T>> {
    var headers: HeadersInit = []
    headers.push(["Content-Type", "application/json"])

    if (!request.isAuth) {
        const token = localStorage.getItem("auth")
        if (token) {
            headers.push(["Authorization", token])
        }
    }

    var data: BodyInit | null = null
    if (request.data) {
        data = JSON.stringify(request.data)
    }

    var requestOptions = {
        method: request.method,
        headers: headers,
        body: data
    }

    const response = await fetch(request.path, requestOptions)
    if (response.status == 401) {
        localStorage.removeItem("auth")
        history.navigate("/login", { replace: true })
        return { error: "Not authorized" }
    } else if (response.status == 204) { // No content
        return {}
    }
    const json = await response.json()
    console.log("Response:\n", json)
    const error = json["error"]
    if (error) {
        return { error: error }
    }

    return { value: json as T }
}