import React from 'react';
import { X, Cpu, Lock, Globe, Server, CheckCircle2, ShieldCheck, ArrowUpRight } from 'lucide-react';

export default function ProductionScalePanel({ isOpen, onClose }) {
  if (!isOpen) return null;

  const pillars = [
    {
      icon: Cpu,
      title: "1. Edge & On-Device Privacy Inference",
      tag: "ZERO-AUDIO EGRESS",
      desc: "For banking apps and telecom endpoints, the LFCC extraction and neural vocoder classification pipeline is compiled to WebAssembly (Wasm) and ONNX-Runtime Web. The user's voice never leaves the client device; only ephemeral 128-byte risk telemetry is sent to the fraud engine.",
      points: [
        "Eliminates central voice wiretapping liability",
        "Sub-15ms inference latency without network round-trips",
        "Compliant with RBI digital lending & DPDP privacy mandates"
      ]
    },
    {
      icon: Lock,
      title: "2. Zero-Knowledge Feature-Only Logging",
      tag: "DATA PRIVACY",
      desc: "In compliance with strict banking secrecy laws, no raw audio or biometric voiceprints are retained in persistent storage. The backend stores only mathematical acoustic statistics (LFCC coefficients, pitch variance, spectral centroid) for post-incident fraud auditing.",
      points: [
        "Ephemeral memory buffers flushed immediately after chunk analysis",
        "SQLite / PostgreSQL tables log only aggregate risk metadata",
        "End-to-end cryptographic audit trails for security compliance"
      ]
    },
    {
      icon: Globe,
      title: "3. Multilingual Indian-Accent Acoustic Models",
      tag: "REGIONAL ADAPTATION",
      desc: "Voice cloning attacks in India exploit regional linguistic nuances (Hindi, Tamil, Telugu, Marathi, Bengali, Hinglish). Our architecture separates phonetic content from acoustic synthesis fingerprints by using language-agnostic Linear Frequency filterbanks, combined with accent-calibrated vocoder baselines.",
      points: [
        "Language-independent detection of neural vocoder phase artifacts",
        "Calibrated pitch intonation thresholds across 12+ Indian regional dialects",
        "Robust against colloquial code-switching (Hinglish/Tanglish)"
      ]
    },
    {
      icon: Server,
      title: "4. Enterprise Banking & Telecom SDKs",
      tag: "SEAMLESS INTEGRATION",
      desc: "Designed as a plug-and-play fraud detection sidecar for Core Banking Systems (CBS), contact centers (Genesys, Cisco, Avaya), and SIP/SS7 telecom switches via high-throughput gRPC and bi-directional WebSockets.",
      points: [
        "gRPC streaming interface processing 10,000+ concurrent calls per cluster",
        "Pre-transaction step-up trigger (e.g. locks high-value NEFT/RTGS wire on critical score)",
        "Unified WebRTC / Web Audio JavaScript SDK for mobile & web banking"
      ]
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800 sticky top-0 bg-slate-900/95 backdrop-blur-sm z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                Production Architecture & Scaling Roadmap
              </h3>
              <p className="text-xs text-slate-400 font-mono">Enterprise Readiness & Regulatory Compliance Overview</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          <div className="p-4 rounded-xl bg-cyan-950/30 border border-cyan-500/30 text-xs text-cyan-200 leading-relaxed">
            <strong>Architecture Summary:</strong> This MVP implements the core real-time acoustic pipeline (LFCC + DSP + Neural Vocoder Classifier). In production banking deployment, the following 4 pillars scale this system to millions of transactions with zero privacy compromise.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pillars.map((pillar, idx) => {
              const Icon = pillar.icon;
              return (
                <div key={idx} className="p-5 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="p-2 rounded-lg bg-slate-800 text-cyan-400">
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-mono font-bold tracking-widest px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                        {pillar.tag}
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-white mb-2">{pillar.title}</h4>
                    <p className="text-xs text-slate-400 leading-relaxed mb-4">{pillar.desc}</p>
                  </div>

                  <div className="space-y-1.5 pt-3 border-t border-slate-800/80">
                    {pillar.points.map((pt, pIdx) => (
                      <div key={pIdx} className="flex items-start gap-2 text-[11px] text-slate-300">
                        <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                        <span>{pt}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <span className="text-xs text-slate-500 font-mono">Voice Sentry AI Enterprise Blueprint v1.0</span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold transition cursor-pointer"
          >
            Close Overview
          </button>
        </div>
      </div>
    </div>
  );
}
