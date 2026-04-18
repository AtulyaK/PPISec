'use client'

import { useFirewallStore } from '../store/firewall'

export default function AuditLog() {
  const { events, clearEvents } = useFirewallStore()

  const decisionStyle = (d: string) =>
    d === 'VETO' ? 'text-red-400 bg-red-500/10 border-red-500/20' :
    d === 'WARN' ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' :
    d === 'PASS' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' :
    'text-slate-400 bg-slate-500/10 border-slate-500/20'

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">Audit Log</h3>
        {events.length > 0 && (
          <button
            onClick={clearEvents}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
        {events.length === 0 && (
          <p className="text-xs text-slate-600 text-center mt-8">No events yet. Send a command.</p>
        )}
        {events.map((e) => (
          <div
            key={e.id}
            className={`rounded-lg border px-3 py-2 text-xs ${decisionStyle(e.decision)}`}
          >
            <div className="flex items-center justify-between mb-0.5">
              <span className="font-bold">{e.decision}</span>
              <span className="opacity-50">{e.latency_ms.toFixed(1)}ms</span>
            </div>
            <p className="opacity-80 font-medium">
              {e.action} → {e.target}
            </p>
            <p className="opacity-50 mt-0.5 text-[10px]">{e.source_modality}</p>
            {e.reason && (
              <p className="opacity-60 mt-1 leading-relaxed">{e.reason}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
