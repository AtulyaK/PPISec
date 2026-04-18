'use client'

import dynamic from 'next/dynamic'
import { useFirewallStore } from '../store/firewall'
import TopBar from '../components/TopBar'
import AuditLog from '../components/AuditLog'
import ArmStatePanel from '../components/ArmStatePanel'
import { TelemetrySocket } from '../components/TelemetrySocket'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, Lock, Activity, Cpu, Bell, Settings } from 'lucide-react'

// Dynamic import for Three.js scene to avoid SSR issues
const Scene3D = dynamic(() => import('../components/Scene3D'), { 
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-slate-950">
      <div className="flex flex-col items-center gap-6">
        <div className="relative">
          <Activity className="w-12 h-12 text-indigo-500 animate-pulse" />
          <div className="absolute inset-0 bg-indigo-500/20 blur-xl animate-pulse" />
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10px] font-black text-white uppercase tracking-[0.5em] ml-2">Initializing_Neural_Link</span>
          <span className="text-[8px] font-mono text-slate-500 uppercase tracking-widest">Awaiting Synchronous Buffer...</span>
        </div>
      </div>
    </div>
  )
})

export default function Dashboard() {
  const { wsConnected } = useFirewallStore()

  return (
    <main className="flex flex-col h-screen bg-[#020617] text-slate-200 overflow-hidden font-sans relative">
      {/* Global Background Ambience */}
      <div className="vignette" />
      
      {/* Background Ambience / Glows */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-500/10 rounded-full blur-[150px] mix-blend-screen" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-500/10 rounded-full blur-[150px] mix-blend-screen" />
      </div>

      {/* Telemetry Socket - Connection logic only */}
      <TelemetrySocket />

      {/* Primary Dashboard Layout */}
      <div className="flex-1 flex flex-col z-10 relative min-h-0">
        {/* Navigation & Global Controls */}
        <TopBar />

        {/* Core Visualization & Surveillance Grid */}
        <div className="flex-1 flex overflow-hidden border-t border-white/[0.03] min-h-0">
          {/* Left Sector: Advanced Audit & Reasoning Trace */}
          <section className="w-[450px] lg:w-[500px] h-full border-r border-white/5 bg-slate-950/20 backdrop-blur-3xl shadow-2xl relative overflow-hidden group">
            <AuditLog />
            
            {/* Sector ID Badge */}
            <div className="absolute bottom-4 left-4 flex gap-4 pointer-events-none opacity-20 group-hover:opacity-40 transition-opacity">
               <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">Sector::SEC_AUDIT_01</span>
               <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">Node::B_SURVEILLANCE</span>
            </div>
          </section>

          {/* Right Sector: 3D Visualization Environment */}
          <section className="flex-1 h-full relative group">
             <Scene3D />
             
             {/* Floating Telemetry HUD */}
             <div className="absolute top-24 right-6 w-64 pointer-events-auto z-20">
                <motion.div 
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex flex-col gap-4"
                >
                   <div className="flex items-center gap-2 mb-2 px-2">
                     <Activity className="w-3.5 h-3.5 text-indigo-500" />
                     <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Hardware_Telemetry</span>
                   </div>
                   <ArmStatePanel />
                </motion.div>
             </div>

             {/* Surveillance Crosshair (Visual Only) */}
             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none opacity-0 group-hover:opacity-10 transition-opacity duration-1000">
                <div className="w-12 h-px bg-white" />
                <div className="h-12 w-px bg-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
             </div>
          </section>
        </div>

        {/* SOC Bottom Status Bar */}
        <footer className="h-10 px-8 flex items-center justify-between border-t border-white/[0.05] bg-black/40 backdrop-blur-2xl">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2.5">
              <Lock className="w-3.5 h-3.5 text-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" />
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-[0.2em]">Gov::AASL_L4_Cert</span>
            </div>
            <div className="h-4 w-px bg-white/10" />
            <div className="flex items-center gap-2.5">
              <Shield className="w-3.5 h-3.5 text-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" />
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-[0.2em]">Firewall::ACTIVE_MONITOR</span>
            </div>
          </div>
          
          <div className="flex items-center gap-10">
             <div className="flex items-center gap-2">
                <Bell className="w-3 h-3 text-slate-600" />
                <span className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest">Alerts::00</span>
             </div>
             <div className="flex items-center gap-4">
               <div className="flex items-center gap-2">
                 <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]" />
                 <span className="text-[9px] font-black text-emerald-500/80 uppercase tracking-widest">Link_Established</span>
               </div>
               <Settings className="w-3.5 h-3.5 text-slate-700 hover:text-indigo-500 transition-colors cursor-pointer" />
             </div>
          </div>
        </footer>
      </div>
    </main>
  )
}
