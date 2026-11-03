import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg:       '#0a0a0f',
        surface:  '#13131a',
        surface2: '#1c1c27',
        border:   '#2a2a3a',
        accent:   '#7b6ef6',
        accent2:  '#f0a500',
        accent3:  '#3dd9a4',
        danger:   '#f05d5d',
        muted:    '#6b6b82',
      },
      fontFamily: {
        head:  ['Syne', 'sans-serif'],
        mono:  ['DM Mono', 'monospace'],
        serif: ['Instrument Serif', 'serif'],
      },
    },
  },
  plugins: [],
}

export default config