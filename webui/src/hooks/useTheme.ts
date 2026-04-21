import { useEffect, useState } from 'react'

export function useTheme() {
    const [theme, setTheme] = useState<'light' | 'dark'>(() =>
        (localStorage.getItem('theme') as 'light' | 'dark') ?? 'light'
    )

    useEffect(() => {
        document.documentElement.setAttribute('data-bs-theme', theme)
        localStorage.setItem('theme', theme)
    }, [theme])

    const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light')

    return { theme, toggleTheme }
}
