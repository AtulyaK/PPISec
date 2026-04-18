'use client'

import dynamic from 'next/dynamic'
import CommandPanel from '../components/CommandPanel'
import AuditLog from '../components/AuditLog'
import ArmStatePanel from '../components/ArmStatePanel'

// Dynamic import because Three.js uses browser APIs (window, WebGL)
const Scene3D = dynamic(() => import('../components/Scene3D'), { ssr: false })

export default function Home() {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* ─── Top Bar ─────────────────────────────────────────────────── */}
      <header className="flex-none flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-900/80 backdrop-blur z-10">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
            <span className="text-xs font-black text-white">SF</span>
          </div>
          <div>
            <h1 className="text-sm font-bold text-white leading-none">Agent Glass</h1>
            <p className="text-[10px] text-slate-400 leading-none mt-0.5">Semantic Firewall — StarHacks 2026</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-[10px] text-slate-500">
          <span>Firewall: <span className="text-indigo-400">4-Stage Pipeline</span></span>
          <span>Model: <span className="text-indigo-400">Qwen2-VL-7B</span></span>
          <span>GPU: <span className="text-indigo-400">AMD MI300X</span></span>
        </div>
      </header>

      {/* ─── Main content ────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">
        {/* Left sidebar: Command panel */}
        <aside className="w-72 flex-none flex flex-col border-r border-slate-800 bg-slate-900/60 p-4 overflow-y-auto">
          <h2 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-3">Control</h2>
          <CommandPanel />
        </aside>

        {/* Center: 3D Viewport */}
        <main className="flex-1 min-w-0 relative">
          {/* Viewport labels */}
          <div className="absolute top-3 left-3 z-10 pointer-events-none">
            <span className="text-[10px] font-mono text-slate-600 uppercase tracking-widest">3D Workspace</span>
          </div>
          <div className="absolute top-3 right-3 z-10 pointer-events-none text-right">
            <span className="text-[10px] font-mono text-slate-600">Drag to orbit · Scroll to zoom</span>
          </div>
          <Scene3D />
        </main>

        {/* Right sidebar: Arm state + Audit log */}
        <aside className="w-72 flex-none flex flex-col border-l border-slate-800 bg-slate-900/60 p-4 gap-4 overflow-hidden">
          <div className="flex-none">
            <h2 className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-3">Arm State</h2>
            <ArmStatePanel />
          </div>
          <div className="flex-1 min-h-0 flex flex-col">
            <AuditLog />
          </div>
        </aside>
      </div>

      {/* ─── Bottom status bar ───────────────────────────────────────── */}
      <footer className="flex-none flex items-center gap-4 px-6 py-2 border-t border-slate-800 bg-slate-900/80 text-[10px] text-slate-500">
        <span>4-stage validation: Policy → MCR → Audio → LTL</span>
        <span className="ml-auto">Fail-safe: any error → VETO</span>
      </footer>
    </div>
  )
}
