/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        background: 'var(--bg-primary)',
        surface: 'var(--bg-secondary)',
        elevated: 'var(--bg-elevated)',
        border: 'var(--border)',
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          ghost: 'var(--text-ghost)',
        },
        accent: {
          crimson: 'var(--accent-red)',
          gold: 'var(--accent-gold)',
          red: 'var(--accent-red)',
          muted: 'var(--accent-muted)',
        }
      },
      fontFamily: {
        sans: ['var(--font-body)', 'sans-serif'],
        serif: ['var(--font-heading)', 'serif'],
        mono: ['var(--font-data)', 'monospace'],
      },
    },
  },
  plugins: [],
}
