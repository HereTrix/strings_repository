import { FC, useRef, useState } from "react"
import { Button, Stack } from "react-bootstrap"

type ToolbarCommand = {
    label: string
    openTag: string
    closeTag: string
    tooltip: string
}

const COMMANDS: ToolbarCommand[] = [
    { label: 'B', openTag: '<b>', closeTag: '</b>', tooltip: 'Bold' },
    { label: 'I', openTag: '<i>', closeTag: '</i>', tooltip: 'Italic' },
    { label: 'U', openTag: '<u>', closeTag: '</u>', tooltip: 'Underline' },
]

function applyTag(
    textarea: HTMLTextAreaElement,
    openTag: string,
    closeTag: string,
    onChange: (value: string) => void
) {
    const { selectionStart: start, selectionEnd: end, value } = textarea
    const selected = value.substring(start, end)
    const wrapped = `${openTag}${selected}${closeTag}`
    const next = value.substring(0, start) + wrapped + value.substring(end)

    onChange(next)

    // Restore cursor — place it after the inserted closing tag if nothing was
    // selected, or select the wrapped content if text was selected.
    requestAnimationFrame(() => {
        textarea.focus()
        if (selected.length > 0) {
            textarea.setSelectionRange(start, start + wrapped.length)
        } else {
            const cursor = start + openTag.length
            textarea.setSelectionRange(cursor, cursor)
        }
    })
}

type MarkdownFieldProps = {
    value: string
    onChange: (value: string) => void
    rows?: number
}

const MarkdownField: FC<MarkdownFieldProps> = ({ value, onChange, rows = 3 }) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const [active, setActive] = useState(false)

    return (
        <div
            onFocus={() => setActive(true)}
            onBlur={() => setActive(false)}
        >
            {active && (
                <Stack direction="horizontal" gap={1} className="mb-1">
                    {COMMANDS.map(cmd => (
                        <Button
                            key={cmd.label}
                            variant="outline-secondary"
                            size="sm"
                            title={cmd.tooltip}
                            style={{
                                fontStyle: cmd.label === 'I' ? 'italic' : 'normal',
                                fontWeight: cmd.label === 'B' ? 'bold' : 'normal',
                                textDecoration: cmd.label === 'U' ? 'underline' : 'none',
                                minWidth: '2rem'
                            }}
                            onMouseDown={e => {
                                // Prevent textarea from losing focus/selection before click fires
                                e.preventDefault()
                                if (textareaRef.current) {
                                    applyTag(textareaRef.current, cmd.openTag, cmd.closeTag, onChange)
                                }
                            }}
                        >
                            {cmd.label}
                        </Button>
                    ))}
                </Stack>
            )}
            <textarea
                ref={textareaRef}
                className="form-control"
                rows={rows}
                style={{ resize: 'vertical' }}
                value={value}
                onChange={e => onChange(e.target.value)}
            />
        </div>
    )
}

export default MarkdownField