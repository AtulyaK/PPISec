'use client'

import { useDemoStore, TelemetryEvent } from '../store/useDemoStore'
import { motion, AnimatePresence } from 'framer-motion'
import { Shield, ShieldAlert, ShieldX, Scan, Eye, Radio, Terminal, Clock, Activity, Fingerprint, MapPin } from 'lucide-react'

const MODALITY_MAP = {
  voice_command: { icon: Radio, label: 'VOICE_INTENT' },
  visual_object: { icon: Eye, label: 'VISUAL_TARGET' },
  visual_text_injection: { icon: Scan, label: 'TEXT_INJECTION' },
  programmatic: { icon: Terminal, label: 'SYSTEM_OP' },
  unknown: { icon: Activity, label: 'ERR_UNKNOWN' },
}

export default function AuditLog() {
  const { events } = useDemoStore()

  return (
    <div className="flex flex-col h-full bg-slate-950/20 backdrop-blur-3xl overflow-hidden">
      {/* Log Header */}
      <div className="px-6 h-12 flex items-center justify-between border-b border-white/[0.05] bg-black/20">
        <div className="flex items-center gap-3">
          <Terminal className="w-3.5 h-3.5 text-indigo-500" />
          <h2 className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-400">Security Audit Trail</h2>
        </div>
        <div className="flex items-center gap-2">
           <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping shadow-[0_0_8px_#6366f1]" />
           <span className="text-[8px] font-mono font-bold text-indigo-400 uppercase tracking-tighter">Live_Stream</span>
        </div>
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="flex flex-col">
          <AnimatePresence initial={false}>
            {events.length === 0 ? (
              <div className="h-full mt-20 flex flex-col items-center justify-center opacity-10 gap-6">
                <Shield className="w-16 h-16" />
                <p className="text-[10px] uppercase font-black tracking-[0.5em]">System Idle // No Active Intakes</p>
              </div>
            ) : (
              events.map((event, idx) => (
                <LogEntry key={event.id} event={event} isLatest={idx === 0} />
              ))
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

function LogEntry({ event, isLatest }: { event: TelemetryEvent, isLatest: boolean }) {
  const modality = MODALITY_MAP[event.source_modality] || MODALITY_MAP.unknown
  const ModalityIcon = modality.icon
  
  const statusConfig = {
    PASS: { color: 'text-emerald-400', glow: 'glow-pass', icon: Shield, hex: '#10b981' },
    WARN: { color: 'text-amber-400', glow: 'glow-warn', icon: ShieldAlert, hex: '#f59e0b' },
    VETO: { color: 'text-red-400', glow: 'glow-veto', icon: ShieldX, hex: '#ef4444' },
    PENDING: { color: 'text-indigo-400', glow: 'glow-idle', icon: Shield, hex: '#6366f1' },
    IDLE: { color: 'text-slate-500', glow: '', icon: Shield, hex: '#64748b' },
  }

  const status = statusConfig[event.decision] || statusConfig.IDLE
  const StatusIcon = status.icon

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      className={`group border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors relative overflow-hidden ${isLatest ? 'bg-indigo-500/[0.03]' : ''}`}
    >
      <div className="p-5 flex items-start gap-4">
        {/* Left Status Pillar */}
        <div className="flex flex-col items-center shrink-0 w-12 pt-1 gap-2">
           <StatusIcon className={`w-5 h-5 ${status.color} ${status.glow}`} />
           <div className={`w-[2px] h-12 bg-gradient-to-b ${status.hex === '#10b981' ? 'from-emerald-500/50' : status.hex === '#ef4444' ? 'from-red-500/50' : 'from-indigo-500/50'} to-transparent`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <span className={`text-[11px] font-black tracking-[0.2em] ${status.color} uppercase`}>
                Protocol::{event.decision}
              </span>
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-white/[0.03] border border-white/[0.05]">
                <ModalityIcon className="w-3 h-3 text-slate-500" />
                <span className="text-[8px] font-mono font-bold text-slate-400 uppercase tracking-tighter">{modality.label}</span>
              </div>
            </div>
            <span className="text-[10px] font-mono font-bold text-slate-600 bg-black/40 px-2 py-0.5 rounded border border-white/[0.03]">{event.latency_ms.toFixed(1)}ms</span>
          </div>

          <h3 className="text-xs font-black text-slate-100 mb-2 uppercase tracking-tight flex items-center gap-2">
            {event.action} <span className="text-indigo-500/50">/</span> {event.target}
          </h3>

          <p className="text-[10px] leading-relaxed text-slate-400 font-medium mb-4 pl-0.5 font-mono italic">
            "{event.reason || 'INTENT_CERTIFIED_BY_GLOBAL_POLICY'}"
          </p>

          <div className="grid grid-cols-2 gap-4">
             <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/20 border border-white/[0.03]">
                <Fingerprint className="w-3 h-3 text-slate-600" />
                <div className="flex flex-col">
                  <span className="text-[7px] font-black text-slate-600 uppercase">Packet ID</span>
                  <span className="text-[8px] font-mono font-bold text-slate-400">{event.id.slice(0, 16)}...</span>
                </div>
             </div>
             <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/20 border border-white/[0.03]">
                <MapPin className="w-3 h-3 text-slate-600" />
                <div className="flex flex-col">
                  <span className="text-[7px] font-black text-slate-600 uppercase">Spatial Coord</span>
                  <span className="text-[8px] font-mono font-bold text-slate-400">X:{event.arm_state.base_x.toFixed(2)} Y:{event.arm_state.base_y.toFixed(2)}</span>
                </div>
             </div>
          </div>
        </div>

        <div className="shrink-0 flex flex-col items-end gap-1 font-mono">
           <span className="text-[10px] font-bold text-slate-600">
             {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
           </span>
           <span className="text-[8px] font-black text-slate-800 uppercase tracking-tighter">NODE_SURVEILLANCE_B</span>
        </div>
      </div>

      {/* Subtle Scanline Animation - only on latest */}
      {isLatest && (
        <div className="absolute inset-0 pointer-events-none opacity-[0.03] bg-gradient-to-t from-indigo-500 via-transparent to-transparent animate-scanline" />
      )}
    </motion.div>
  )
}
