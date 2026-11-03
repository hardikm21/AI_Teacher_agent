import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Teacher Agent',
  description: 'Personalised project-based learning powered by LangGraph',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}