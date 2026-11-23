// Light/dark toggle. Light is the default (Alli, Nov 21); dark is there for people who
// prefer it, and their pick is remembered.
type Theme = 'light' | 'dark'
const KEY = 'trip-planner-theme'

export function useTheme() {
  const theme = useState<Theme>('theme', () => 'light')

  function apply(t: Theme) {
    theme.value = t
    document.documentElement.classList.toggle('dark', t === 'dark')
  }

  function init() {
    let saved: string | null = null
    try { saved = localStorage.getItem(KEY) } catch { /* private mode */ }
    apply(saved === 'dark' ? 'dark' : 'light')
  }

  function toggle() {
    const next: Theme = theme.value === 'dark' ? 'light' : 'dark'
    apply(next)
    try { localStorage.setItem(KEY, next) } catch { /* ignore */ }
  }

  return { theme, init, toggle }
}
