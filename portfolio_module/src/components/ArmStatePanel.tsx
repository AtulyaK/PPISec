'use client'

import { useDemoStore } from '../store/useDemoStore'
import { motion } from 'framer-motion'
import { Move, GripHorizontal, Box } from 'lucide-react'

export default function ArmStatePanel() {
  const { armState } = useDemoStore()

  const fields = [
    { label: 'Base X', value: armState.base_x?.toFixed(2) || '0.00', unit: 'm' },
    { label: 'Base Y', value: armState.base_y?.toFixed(2) || '0.00', unit: 'm' },
    { label: 'Arm Z', value: armState.arm_z?.toFixed(2) || '1.20', unit: 'm' },
  ]

  return (
    <div className="flex flex-col gap-4">
      {/* XYZ coordinates - Digital Readout */}
      <div className="grid grid-cols-1 gap-2">
        {fields.map((f) => (
          <div key={f.label} className="glass-card px-4 py-3 flex items-center justify-between border-white/5">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em]">{f.label}</span>
            <div className="flex items-baseline gap-1">
              <span className="text-lg font-mono font-black text-indigo-400 tabular-nums leading-none">
                {f.value}
              </span>
              <span className="text-[9px] font-bold text-slate-600 uppercase">{f.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Held Object / Extent */}
      <div className="glass-card px-4 py-3 flex items-center justify-between border-white/5">
        <div className="flex items-center gap-2">
          <Box className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest leading-none">Held Object</span>
        </div>
        <span className={`text-[11px] font-bold ${armState.held_object ? 'text-amber-400' : 'text-slate-600'}`}>
          {armState.held_object?.toUpperCase() || 'NONE'}
        </span>
      </div>

      {/* Gripper + Status Row */}
      <div className="grid grid-cols-2 gap-2">
        <div className="glass-card px-4 py-4 flex flex-col gap-2 border-white/5 relative overflow-hidden">
          <div className="flex items-center gap-2 text-slate-500">
            <GripHorizontal className="w-3.5 h-3.5" />
            <span className="text-[9px] font-bold uppercase tracking-widest leading-none">Gripper</span>
          </div>
          <div className={`text-xs font-black tracking-widest transition-colors duration-500 ${armState.gripper_open ? 'text-amber-400' : 'text-emerald-400'}`}>
            {armState.gripper_open ? 'OPEN' : 'LOCKED'}
          </div>
          <div className={`absolute bottom-0 left-0 h-0.5 w-full transition-all duration-500 ${armState.gripper_open ? 'bg-amber-400/30' : 'bg-emerald-400/30'}`} />
        </div>

        <div className="glass-card px-4 py-4 flex flex-col gap-2 border-white/5 relative overflow-hidden">
          <div className="flex items-center gap-2 text-slate-500">
            <Move className="w-3.5 h-3.5" />
            <span className="text-[9px] font-bold uppercase tracking-widest leading-none">Motion</span>
          </div>
          <div className={`text-xs font-black tracking-widest transition-colors duration-500 ${armState.is_navigating || armState.is_arm_moving ? 'text-indigo-400' : 'text-slate-500'}`}>
            {armState.is_navigating ? 'NAVIGATING' : armState.is_arm_moving ? 'MOVING ARM' : 'STATIC'}
          </div>
          {(armState.is_navigating || armState.is_arm_moving) && (
            <motion.div 
              animate={{ x: ['-100%', '100%'] }}
              transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
              className="absolute bottom-0 left-0 h-0.5 w-full bg-indigo-500/50" 
            />
          )}
        </div>
      </div>

      {/* Action Detail */}
      <div className="glass-card px-4 py-4 border-white/5">
        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest block mb-2">Operation Mode</span>
        <div className="flex items-center gap-2">
          <div className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono font-bold border border-indigo-500/20">
            {armState.last_action.toUpperCase()}
          </div>
          {armState.last_target !== 'none' && (
            <>
              <span className="text-slate-600 text-[10px]">→</span>
              <span className="text-slate-300 text-[11px] font-medium tracking-tight"> {armState.last_target}</span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
