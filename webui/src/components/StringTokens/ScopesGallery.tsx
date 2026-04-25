import { FC, useEffect, useState } from "react"
import { Badge, Card, Col, Row } from "react-bootstrap"
import { APIMethod, http } from "../../utils/network"
import Scope from "../../types/Scope"
import ErrorAlert from "../UI/ErrorAlert"

type ScopesGalleryProps = {
    project_id: string
    onScopeSelect: (scope: Scope) => void
}

const ScopesGallery: FC<ScopesGalleryProps> = ({ project_id, onScopeSelect }) => {
    const [scopes, setScopes] = useState<Scope[]>([])
    const [error, setError] = useState<string>()

    useEffect(() => {
        const fetchScopes = async () => {
            const result = await http<Scope[]>({
                method: APIMethod.get,
                path: `/api/project/${project_id}/scopes`,
            })
            if (result.value) setScopes(result.value)
            else setError(result.error)
        }
        fetchScopes()
    }, [project_id])

    return (
        <>
            {scopes.length === 0 ? (
                <p className="text-muted mt-3">No scopes defined for this project.</p>
            ) : (
                <Row xs={1} sm={2} md={3} lg={4} className="g-3 mt-2">
                    {scopes.map(scope => (
                        <Col key={scope.id}>
                            <Card
                                style={{ cursor: 'pointer' }}
                                className="h-100"
                                onClick={() => onScopeSelect(scope)}
                            >
                                {scope.images[0] && (
                                    <Card.Img
                                        variant="top"
                                        src={scope.images[0].url}
                                        style={{ height: '120px', objectFit: 'cover' }}
                                    />
                                )}
                                <Card.Body>
                                    <Card.Title className="fs-6">{scope.name}</Card.Title>
                                    {scope.description && (
                                        <Card.Text className="small text-muted text-truncate">
                                            {scope.description}
                                        </Card.Text>
                                    )}
                                    <Badge bg="secondary">
                                        {scope.token_count} token{scope.token_count !== 1 ? 's' : ''}
                                    </Badge>
                                </Card.Body>
                            </Card>
                        </Col>
                    ))}
                </Row>
            )}
            {error && <ErrorAlert error={error} onClose={() => setError(undefined)} />}
        </>
    )
}

export default ScopesGallery
