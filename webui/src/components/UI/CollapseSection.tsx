import { FC, ReactNode, useState } from "react"
import { Button, Collapse, Container, Stack } from "react-bootstrap"

type CollapseSectionProps = {
    title: string
    children: ReactNode
    defaultOpen?: boolean
}

const CollapseSection: FC<CollapseSectionProps> = ({ title, children, defaultOpen = false }) => {
    const [open, setOpen] = useState(defaultOpen)

    return (
        <Container className="square border rounded-3 my-2">
            <Stack
                direction="horizontal"
                gap={3}
                onClick={() => setOpen(v => !v)}
                className="my-2"
            >
                <label>{title}</label>
                <Button className="ms-auto" onClick={e => { e.stopPropagation(); setOpen(v => !v) }}>
                    {open ? "Collapse" : "Reveal"}
                </Button>
            </Stack>
            <Collapse in={open}>
                <div className="my-2">{children}</div>
            </Collapse>
        </Container>
    )
}

export default CollapseSection
