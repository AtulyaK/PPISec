import type { Metadata } from 'next'
import './globals.css'
import { TelemetrySocket } from '../components/TelemetrySocket'

export const metadata: Metadata = {
  title: 'Agent Glass — Semantic Firewall Dashboard',
  description: 'Real-time VLA security monitoring and robotic arm visualization',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-[#020817] text-white antialiased font-sans">
        <TelemetrySocket />
        {children}
      </body>
    </html>
  )
}
