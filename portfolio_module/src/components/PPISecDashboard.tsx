'use client';

import React, { useEffect, useState } from 'react';
import Scene3D from './Scene3D';
import CommandPanel from './CommandPanel';
import AuditLog from './AuditLog';
import ArmStatePanel from './ArmStatePanel';
import { useAgentLoop } from '../brain/useAgentLoop';
import { useDemoStore } from '../store/useDemoStore';
import { Shield, Loader2, ServerCog } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function PPISecDashboard() {
  const { initializeEngine, isLoaded } = useAgentLoop();
  const [loadProgress, setLoadProgress] = useState<any>(null);

  useEffect(() => {
    // Start downloading and caching the Transformers.js model as soon as the component mounts
    initializeEngine((progressData) => {
      setLoadProgress(progressData);
    });
  }, [initializeEngine]);

  return (
    <div className="w-full h-full min-h-[600px] flex flex-col bg-[#020617] text-white overflow-hidden font-sans">
      
      {/* ─── Boot Sequence Overlay ─── */}
      <AnimatePresence>
        {!isLoaded && (
          <motion.div 
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#020617] backdrop-blur-md"
          >
            <Shield className="w-16 h-16 text-indigo-500 mb-6 animate-pulse" />
            <h1 className="text-2xl font-black uppercase tracking-[0.2em] mb-2">PPISec Firewall</h1>
            <p className="text-slate-400 text-sm mb-8 max-w-md text-center">
              Booting client-side Security Governance Engine. Downloading WebAssembly NLP models (approx 20MB)...
            </p>
            
            {loadProgress && loadProgress.status !== 'ready' && (
              <div className="w-64">
                <div className="flex justify-between text-xs text-slate-500 mb-2">
                  <span>{loadProgress.file || 'Initializing...'}</span>
                  <span>{loadProgress.progress ? `${Math.round(loadProgress.progress)}%` : ''}</span>
                </div>
                <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-indigo-500 transition-all duration-300"
                    style={{ width: `${loadProgress.progress || 0}%` }}
                  />
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Main Dashboard ─── */}
      <header className="h-14 shrink-0 flex items-center justify-between px-6 border-b border-white/[0.05] bg-black/40 z-10">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-indigo-500" />
          <div className="flex flex-col">
            <h1 className="text-xs font-black uppercase tracking-[0.2em] leading-none">PPISec Semantic Firewall</h1>
            <span className="text-[9px] text-slate-500 uppercase font-bold tracking-widest mt-0.5">100% Client-Side Engine</span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-[10px] text-slate-500 uppercase font-bold tracking-widest">
          <span className="flex items-center gap-1.5"><ServerCog className="w-3 h-3 text-indigo-400"/> Zero Backend</span>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Left Column: 3D Visualization */}
        <div className="flex-1 relative border-r border-white/[0.05]">
          <Scene3D />
        </div>

        {/* Right Column: Controls & Audit */}
        <div className="w-96 shrink-0 flex flex-col bg-black/20">
          <div className="h-[45%] border-b border-white/[0.05] relative z-20">
            <CommandPanel />
          </div>
          <div className="h-[55%] relative z-10">
            <AuditLog />
          </div>
        </div>
      </div>
    </div>
  );
}
