import React from 'react';
import { ShieldCheck, Info } from 'lucide-react';

export default function Navbar({ transactionContext, noiseReductionActive, onOpenScalePanel }) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-40 px-4 lg:px-8 py-3.5">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Left: Brand */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.25)]">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-wider text-white flex items-center gap-2">
                VOICE_INTEGRITY <span className="text-cyan-400 font-black">AI</span>
              </h1>
            </div>
            <p className="text-xs text-slate-400 font-mono">Monitoring command center</p>
          </div>
        </div>

        <nav className="hidden lg:flex items-center gap-5" aria-label="Primary navigation">
          <span className="cyber-status border-b-2 border-pink-500 pb-1">MONITORING</span>
          <span className="text-xs text-slate-400 font-mono hover:text-pink-400 transition">ANALYTICS</span>
          <span className="text-xs text-slate-400 font-mono hover:text-pink-400 transition">WORKFLOW</span>
          <span className="text-xs text-slate-400 font-mono hover:text-pink-400 transition">API</span>
        </nav>

        {/* Right: Production Architecture Modal Trigger */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenScalePanel}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-slate-600 transition shadow-sm"
          >
            <Info className="w-4 h-4 text-cyan-400" />
            <span>How This Scales to Production</span>
          </button>
        </div>
      </div>
    </header>
  );
}
