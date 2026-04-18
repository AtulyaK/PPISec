'use client'

import { useFirewallStore } from '../store/firewall'

export default function ArmStatePanel() {
  const { armState, wsConnected, isProcessing } = useFirewallStore()

  const fields = [
    { label: 'X', value: armState.x.toFixed(1), unit: 'mm' },
    { label: 'Y', value: armState.y.toFixed(1), unit: 'mm' },
    { label: 'Z', value: armState.z.toFixed(1), unit: 'mm' },
  ]

  return (
    <div className="flex flex-col gap-3">
      {/* Connection status */}
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
        <span className="text-xs text-slate-400">
          {wsConnected ? 'Live' : 'Disconnected'}
        </span>
        {isProcessing && (
          <span className="ml-auto text-xs text-indigo-400 animate-pulse">Processing…</span>
        )}
      </div>

      {/* XYZ coordinates */}
      <div className="grid grid-cols-3 gap-2">
        {fields.map((f) => (
          <div key={f.label} className="rounded-lg bg-slate-800/60 border border-slate-700 px-3 py-2">
            <span className="text-[10px] text-slate-500 uppercase tracking-widest">{f.label}</span>
            <div className="text-sm font-mono font-bold text-indigo-300 mt-0.5">
              {f.value}
              <span className="text-[10px] text-slate-500 ml-0.5">{f.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Gripper + action */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-slate-800/60 border border-slate-700 px-3 py-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">Gripper</span>
          <div className={`text-sm font-bold mt-0.5 ${armState.gripper_open ? 'text-amber-400' : 'text-emerald-400'}`}>
            {armState.gripper_open ? '○ Open' : '● Closed'}
          </div>
        </div>
        <div className="rounded-lg bg-slate-800/60 border border-slate-700 px-3 py-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">Status</span>
          <div className={`text-sm font-bold mt-0.5 ${armState.is_moving ? 'text-indigo-400 animate-pulse' : 'text-slate-400'}`}>
            {armState.is_moving ? '⟳ Moving' : '◉ Idle'}
          </div>
        </div>
      </div>

      {/* Last action */}
      <div className="rounded-lg bg-slate-800/60 border border-slate-700 px-3 py-2">
        <span className="text-[10px] text-slate-500 uppercase tracking-widest">Last Action</span>
        <div className="text-xs font-medium text-slate-300 mt-0.5">
          <span className="text-indigo-400">{armState.last_action}</span>
          {armState.last_target !== 'none' && (
            <> → <span className="text-slate-400">{armState.last_target}</span></>
          )}
        </div>
      </div>
    </div>
  )
}
