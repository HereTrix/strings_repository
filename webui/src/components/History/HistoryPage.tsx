import { FC, useState } from "react"
import Project from "../model/Project"
import { Button, Container, Form, Stack, Table } from "react-bootstrap"
import { APIMethod, download, http } from "../Utils/network"
import fileDownload from "js-file-download"
import ErrorAlert from "../UI/ErrorAlert"

type HistoryPageProps = {
    project: Project
}

interface HistoryData {
    updated_at: string
    language: string
    token: string
    editor: string
    status: string
    old_value: string | undefined
    new_value: string
}

const HistoryPage: FC<HistoryPageProps> = ({ project }) => {

    const [error, setError] = useState<string>()
    const [data, setData] = useState<Map<string, HistoryData[]>>()

    const [dateFrom, setDateFrom] = useState<string>()
    const [dateTo, setDateTo] = useState<string>()

    const requestParams = () => {
        var params = new Map<string, string>()

        if (dateFrom) {
            params.set('from', dateFrom)
        }

        if (dateTo) {
            params.set('to', dateTo)
        }
        return params
    }

    const loadHistory = async () => {

        const result = await http<HistoryData[]>({
            method: APIMethod.get,
            path: `/api/project/${project.id}/history`,
            params: requestParams()
        })

        if (result.value) {
            const grouped = new Map<string, HistoryData[]>();

            result.value.forEach(obj => {
                var value = grouped.get(obj.token)
                if (!value) {
                    value = []
                }
                value.push(obj)
                grouped.set(obj.token, value);
            });
            setData(grouped)
        } else {
            setError(result.error)
        }
    }

    const exportHistory = async () => {
        const result = await download({
            method: APIMethod.get,
            path: `/api/project/${project.id}/history/export`,
            params: requestParams()
        })

        if (result.value) {
            fileDownload(result.value.content, result.value.name)
        } else {
            setError(result.error)
        }
    }

    return (
        <>
            <Container
                className="d-flex justify-content-between align-items-end my-2">
                <Stack direction="horizontal" gap={2} className="align-items-end">
                    <Container>
                        <label>From date:</label>
                        <Form.Control
                            type="date"
                            onChange={(e) => setDateFrom(e.target.value)} />
                    </Container>
                    <Container>
                        <label>To date:</label>
                        <Form.Control
                            type="date"
                            onChange={(e) => setDateTo(e.target.value)} />
                    </Container>
                    <Button onClick={loadHistory}>Show</Button>
                </Stack>
                <Button onClick={exportHistory}>Export history</Button>
            </Container>
            {data && [...data.keys()].map((key) => {
                const value = data.get(key)
                return <Container key={key}>
                    <h2>{key}</h2>
                    <Table>
                        <thead>
                            <tr>
                                <th>Updated at:</th>
                                <th>Language</th>
                                <th>Old translation</th>
                                <th>New translation</th>
                                <th>Editor</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {value && value.map((item) =>
                                <tr key={item.token + item.updated_at}>
                                    <td>{item.updated_at}</td>
                                    <td>{item.language}</td>
                                    <td>{item.old_value}</td>
                                    <td>{item.new_value}</td>
                                    <td>{item.editor}</td>
                                    <td>{item.status}</td>
                                </tr>
                            )}
                        </tbody>
                    </Table>
                </Container>
            })}
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </>
    )
}

export default HistoryPage