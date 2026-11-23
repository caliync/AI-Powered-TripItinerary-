import type { Config } from 'tailwindcss'

const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  darkMode: 'class',
  content: ['./components/**/*.vue', './layouts/**/*.vue', './pages/**/*.vue', './app.vue'],
  theme: {
    extend: {
      colors: {
        bg: v('bg'),
        soft: v('soft'),
        surface: v('surface'),
        ink: v('ink'),
        muted: v('muted'),
        line: v('line'),
        lake: v('lake'),
        'lake-soft': v('lake-soft'),
        'lake-deep': v('lake-deep'),
        mango: v('mango'),
        moss: v('moss'),
        caution: v('caution'),
        danger: v('danger'),
      },
      fontFamily: { sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'] },
      borderRadius: { card: '16px', pill: '999px' },
      boxShadow: { lift: 'var(--shadow)' },
      maxWidth: { page: '78rem' },
    },
  },
} satisfies Config
