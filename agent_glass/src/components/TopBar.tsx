'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useFirewallStore, SourceModality } from '../store/firewall'
import { SCENARIOS } from '../data/scenarios'
import { Send, Terminal, Cpu, Globe, Zap, ShieldCheck, AlertTriangle, Ban, Activity, Radio, Eye, Scan } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_BRAIN_URL ?? 'http://localhost:8002'

export default function TopBar() {
  const { 
    isProcessing, 
    setProcessing, 
    lastDecision, 
    lastLatencyMs, 
    activeScenario, 
    setScenario,
    wsConnected 
  } = useFirewallStore()
  
  const [command, setCommand] = useState('')
  const [modality, setModality] = useState<SourceModality>('voice_command')

  async function submitCommand() {
    if (!command.trim() || isProcessing) return
    setProcessing(true)
    try {
      const res = await fetch(`${API_URL}/start_task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          transcript: command, 
          source_modality: modality,
          scenario: activeScenario.id
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
       setCommand('')
    } catch (e) {
      console.error('[TopBar] Failed to send command', e)
      setProcessing(false)
    }
  }

  const statusConfig = {
    PASS: { color: 'text-emerald-400', glow: 'glow-pass', icon: ShieldCheck, label: 'SECURE' },
    WARN: { color: 'text-amber-400', glow: 'glow-warn', icon: AlertTriangle, label: 'CONFLICT' },
    VETO: { color: 'text-red-400', glow: 'glow-veto', icon: Ban, label: 'BLOCKED' },
    PENDING: { color: 'text-indigo-400', glow: 'glow-idle', icon: Zap, label: 'AUDITING' },
    IDLE: { color: 'text-slate-500', glow: '', icon: Globe, label: 'STANDBY' },
  }

  const currentStatus = statusConfig[lastDecision as keyof typeof statusConfig] || statusConfig.IDLE

  return (
    <header className="flex flex-col border-b border-white/5 bg-slate-950/20 backdrop-blur-3xl z-50">
      {/* Infrastructure Bar */}
      <div className="h-9 px-6 flex items-center justify-between bg-black/40 border-b border-white/[0.03]">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]'}`} />
            <span className="text-[9px] font-mono font-bold text-slate-400 tracking-wider uppercase">NET: {wsConnected ? 'LINK_UP' : 'LINK_DOWN'}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-500">
            <Cpu className="w-3 h-3" />
            <span className="text-[9px] font-mono font-bold tracking-wider uppercase">CORE: QWEN2-VL-7B</span>
          </div>
        </div>

        <div className="flex items-center gap-5">
           <div className={`flex items-center gap-2 px-3 py-0.5 rounded-sm border border-white/5 transition-all duration-700 ${lastDecision !== 'IDLE' ? 'bg-white/5' : ''}`}>
              <currentStatus.icon className={`w-3 h-3 ${currentStatus.color}`} />
              <span className={`text-[9px] font-black tracking-[0.2em] ${currentStatus.color} ${currentStatus.glow}`}>{currentStatus.label}</span>
           </div>
           <div className="flex items-center gap-3">
             <div className="flex flex-col items-end leading-none">
               <span className="text-[7px] font-black text-slate-600 uppercase tracking-tighter">Latency</span>
               <span className="text-[10px] font-mono font-bold text-slate-400">{lastLatencyMs.toFixed(1)}ms</span>
             </div>
             <Activity className="w-3.5 h-3.5 text-slate-700" />
           </div>
        </div>
      </div>

      {/* Control Bar */}
      <div className="h-14 px-4 flex items-center gap-4">
        {/* Scenario Selection */}
        <div className="flex items-center gap-3 h-full px-2">
          <Globe className="w-4 h-4 text-indigo-400 opacity-50" />
          <div className="flex flex-col">
            <span className="text-[7px] font-black text-slate-600 uppercase tracking-widest ml-0.5">Deployment</span>
            <select 
              value={activeScenario.id}
              onChange={(e) => {
                const s = SCENARIOS.find(x => x.id === e.target.value)
                if (s) setScenario(s)
              }}
              className="bg-transparent border-none text-xs font-black text-white focus:outline-none cursor-pointer hover:text-indigo-400 transition-colors uppercase tracking-tight"
            >
              {SCENARIOS.map(s => (
                <option key={s.id} value={s.id} className="bg-slate-900 text-white font-sans">{s.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="h-8 w-px bg-white/5" />

        {/* Action Input Area */}
        <div className="flex-1 flex items-center gap-4 group h-full">
          <Terminal className="w-4 h-4 text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
          <div className="relative flex-1 h-full flex items-center">
            <input 
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitCommand()}
              placeholder="Awaiting directive for autonomous unit..."
              className="w-full bg-transparent border-none text-xs text-white placeholder:text-slate-600 focus:outline-none font-medium selection:bg-indigo-500/50"
            />
            
            <AnimatePresence>
              {command && (
                <motion.div 
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="flex items-center gap-2"
                >
                  <div className="flex items-center gap-1.5 p-1 rounded-lg bg-black/40 border border-white/5">
                    {[
                      { id: 'voice_command', icon: Radio, mod: 'voice' },
                      { id: 'visual_object', icon: Eye, mod: 'visual' },
                      { id: 'visual_text_injection', icon: Scan, mod: 'trojan' },
                    ].map((m) => (
                      <button
                        key={m.id}
                        onClick={() => setModality(m.id as SourceModality)}
                        className={`p-1.5 rounded-md transition-all ${modality === m.id ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'text-slate-500 hover:text-slate-300'}`}
                        title={m.mod}
                      >
                        <m.icon className="w-3.5 h-3.5" />
                      </button>
                    ))}
                  </div>

                  <button 
                    onClick={submitCommand}
                    disabled={isProcessing}
                    className="h-10 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-xl shadow-indigo-600/20 transition-all active:scale-95 disabled:opacity-50 flex items-center gap-2"
                  >
                    {isProcessing ? <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}><Cpu className="w-4 h-4" /></motion.div> : <Send className="w-4 h-4" />}
                    <span className="text-[10px] font-black uppercase tracking-widest">Transmit</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <div className="h-8 w-px bg-white/5" />

        {/* Global Navigation Presets */}
        <div className="flex gap-2 mr-2">
           <button 
             onClick={() => { setCommand('Return to base'); setModality('voice_command'); }}
             className="px-4 py-2 rounded-lg text-[9px] font-black text-slate-500 hover:text-white hover:bg-white/5 transition-all uppercase tracking-widest border border-white/5 border-dashed"
           >
             RTB_PROT
           </button>
           <button 
             onClick={() => { setCommand('Status report'); setModality('voice_command'); }}
             className="px-4 py-2 rounded-lg text-[9px] font-black text-slate-500 hover:text-white hover:bg-white/5 transition-all uppercase tracking-widest border border-white/5 border-dashed"
           >
             SYS_DIAG
           </button>
        </div>
      </div>
      
      {/* Progress Line */}
      <AnimatePresence>
        {isProcessing && (
          <motion.div 
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            exit={{ scaleX: 0, opacity: 0 }}
            className="h-[1px] w-full bg-indigo-500 origin-left shadow-[0_0_10px_#6366f1]"
          />
        )}
      </AnimatePresence>
    </header>
  )
}
