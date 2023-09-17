import { FC, useState } from "react"
import Project from "../model/Project"
import { Button, Container, Form, Stack, Table } from "react-bootstrap"
import { APIMethod, download, http } from "../Utils/network"
import fileDownload from "js-file-download"

type HistoryPageProps = {
    project: Project
}

interface HistoryData {
    translation: string
    updated_at: string
    language: string
    token: string
}

const HistoryPage: FC<HistoryPageProps> = ({ project }) => {

    const [data, setData] = useState<HistoryData[]>()

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
            setData(result.value)
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
                <Button onClick={exportHistory}>Export</Button>
            </Container>
            <Table>
                <thead>
                    <tr>
                        <th>Updated at:</th>
                        <th>Language</th>
                        <th>Localization key</th>
                        <th>Translation</th>
                    </tr>
                </thead>
                <tbody>
                    {data && data.map((item) =>
                        <tr key={item.language + item.token}>
                            <td>{item.updated_at}</td>
                            <td>{item.language}</td>
                            <td>{item.token}</td>
                            <td>{item.translation}</td>
                        </tr>
                    )}
                </tbody>
            </Table>
        </>
    )
}

export default HistoryPage