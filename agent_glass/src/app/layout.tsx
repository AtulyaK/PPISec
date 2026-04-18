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
      <body className="bg-[#020817] text-white antialiased">
        <TelemetrySocket />
        {children}
      </body>
    </html>
  )
}
