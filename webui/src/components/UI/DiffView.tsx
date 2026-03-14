import { FC } from "react";

type DiffSpan = { type: 'equal' | 'added' | 'removed'; text: string }

function wordDiff(base: string, next: string): DiffSpan[] {
    const a = base.split(/(\s+)/)
    const b = next.split(/(\s+)/)

    // Simple LCS-based diff
    const m = a.length, n = b.length
    const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))
    for (let i = m - 1; i >= 0; i--)
        for (let j = n - 1; j >= 0; j--)
            dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])

    const result: DiffSpan[] = []
    let i = 0, j = 0
    while (i < m || j < n) {
        if (i < m && j < n && a[i] === b[j]) {
            result.push({ type: 'equal', text: a[i] })
            i++; j++
        } else if (j < n && (i >= m || dp[i + 1]?.[j] <= dp[i]?.[j + 1])) {
            result.push({ type: 'added', text: b[j] })
            j++
        } else {
            result.push({ type: 'removed', text: a[i] })
            i++
        }
    }
    return result
}

type DiffViewProps = { base: string; next: string }

const DiffView: FC<DiffViewProps> = ({ base, next }) => {
    const spans = wordDiff(base, next)
    return (
        <span style={{ fontFamily: 'monospace', fontSize: '0.85em', lineHeight: 1.6 }}>
            {spans.map((s, i) => {
                if (s.type === 'equal') return <span key={i}>{s.text}</span>
                if (s.type === 'added') return (
                    <span key={i} style={{ background: '#d4edda', color: '#155724', borderRadius: 2, padding: '0 2px' }}>
                        {s.text}
                    </span>
                )
                return (
                    <span key={i} style={{ background: '#f8d7da', color: '#721c24', borderRadius: 2, padding: '0 2px', textDecoration: 'line-through' }}>
                        {s.text}
                    </span>
                )
            })}
        </span>
    )
}

export default DiffView