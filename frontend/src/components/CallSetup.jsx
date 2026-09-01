import React, { useState } from 'react';
import { 
  PhoneCall, 
  UploadCloud, 
  ShieldAlert, 
  KeyRound, 
  CreditCard, 
  Lock, 
  FileAudio, 
  Play, 
  ArrowRight,
  Radio,
  Zap,
  Users
} from 'lucide-react';

export default function CallSetup({ 
  onStartModeA, 
  onStartModeB, 
  transactionContext, 
  setTransactionContext,
  loading 
}) {
  const [activeTab, setActiveTab] = useState('mode_a');
  const [selectedFile, setSelectedFile] = useState(null);
  const [roomCodeInput, setRoomCodeInput] = useState('');

  const contexts = [
    {
      id: 'general',
      name: 'General Call',
      desc: 'Standard conversation. CRITICAL threshold >60%.',
      icon: Lock,
      color: 'border-slate-700 hover:border-slate-500 bg-slate-900/60'
    },
    {
      id: 'credential_reset',
      name: 'Credential Reset',
      desc: 'Password or PIN modification. CRITICAL threshold >60%.',
      icon: KeyRound,
      color: 'border-yellow-500/30 hover:border-yellow-500/60 bg-yellow-950/20'
    },
    {
      id: 'otp_share',
      name: 'OTP / 2FA Verification',
      desc: 'Disclosing authentication codes. CRITICAL threshold >60%.',
      icon: ShieldAlert,
      color: 'border-orange-500/30 hover:border-orange-500/60 bg-orange-950/20'
    },
    {
      id: 'fund_transfer',
      name: 'Fund Transfer / Wire',
      desc: 'Financial payments and authorizations. CRITICAL threshold >60%.',
      icon: CreditCard,
      color: 'border-red-500/30 hover:border-red-500/60 bg-red-950/20'
    }
  ];

  const handleFileUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      {/* Hero Title */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-400 text-xs font-mono mb-3">
          <Zap className="w-3.5 h-3.5" />
          <span>REAL-TIME MULTI-BAND ACOUSTIC INFERENCE</span>
        </div>
        <h2 className="text-3xl lg:text-4xl font-extrabold text-white tracking-tight">
          AI Voice Impersonation Defense
        </h2>
        <p className="text-slate-400 text-sm max-w-xl mx-auto mt-2">
          Continuously evaluates conversational audio stream in 2.5s chunks. Detects neural vocoder phase ripple,
          linear-frequency (LFCC) spectral anomalies, and synthetic pitch flatness.
        </p>
      </div>

      {/* Step 1: Transaction Context Selection */}
      <div className="mb-8">
        <label className="block text-xs font-mono uppercase tracking-widest text-slate-400 mb-3">
          Step 1: Select Transaction Risk Context
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {contexts.map((ctx) => {
            const Icon = ctx.icon;
            const isSelected = transactionContext === ctx.id;
            return (
              <button
                key={ctx.id}
                type="button"
                onClick={() => setTransactionContext(ctx.id)}
                className={`p-4 rounded-xl border text-left transition-all relative cursor-pointer ${
                  isSelected
                    ? 'border-cyan-400 bg-cyan-950/40 ring-1 ring-cyan-400/50 shadow-[0_0_20px_rgba(6,182,212,0.15)]'
                    : ctx.color
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <Icon className={`w-5 h-5 ${isSelected ? 'text-cyan-400' : 'text-slate-400'}`} />
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#06b6d4]"></span>
                  )}
                </div>
                <h4 className="text-sm font-semibold text-white">{ctx.name}</h4>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{ctx.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step 2: Mode Tabs */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 lg:p-8 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-5 mb-6">
          <div>
            <label className="block text-xs font-mono uppercase tracking-widest text-slate-400">
              Step 2: Choose Call Mode
            </label>
            <div className="flex gap-4 mt-2">
              <button
                onClick={() => setActiveTab('mode_a')}
                className={`text-lg font-bold pb-2 ${activeTab === 'mode_a' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400 hover:text-slate-300'}`}
              >
                Mode A (Replay)
              </button>
              <button
                onClick={() => setActiveTab('mode_b')}
                className={`text-lg font-bold pb-2 ${activeTab === 'mode_b' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-slate-400 hover:text-slate-300'}`}
              >
                Mode B (Live WebRTC)
              </button>
            </div>
          </div>
        </div>

        {/* Tab Content: Mode A (Upload & Simulated Replay) */}
        {activeTab === 'mode_a' && (
          <div className="space-y-6">
            {/* Custom Upload Dropzone */}
            <div className="border-2 border-dashed border-slate-700 hover:border-cyan-500/50 rounded-xl p-6 text-center bg-slate-950/30 transition">
              <UploadCloud className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
              <p className="text-xs font-semibold text-white">Upload Call Audio File (.wav, .mp3, .ogg)</p>
              <p className="text-[11px] text-slate-400 mt-1">Backend will simulate real-time live streaming playback</p>
              
              <input
                type="file"
                id="audio-upload"
                accept=".wav,.mp3,.ogg,.m4a,.webm"
                onChange={handleFileUpload}
                className="hidden"
              />
              <label
                htmlFor="audio-upload"
                className="mt-3 inline-block px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs font-mono cursor-pointer border border-slate-700"
              >
                {selectedFile ? selectedFile.name : 'Browse Audio Files'}
              </label>

              {selectedFile && (
                <div className="mt-4">
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => onStartModeA(selectedFile)}
                    className="py-2.5 px-6 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition shadow-lg inline-flex items-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    <span>{loading ? 'Uploading...' : `Stream & Analyze "${selectedFile.name}"`}</span>
                  </button>
                </div>
              )}
            </div>

            {/* Quick Demo Presets */}
            <div>
              <label className="block text-xs font-mono uppercase tracking-widest text-slate-400 mb-2.5">
                Or Instant-Test With Calibrated Demo Clips:
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => onStartModeA('sample_human_clean.wav')}
                  className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-950/20 hover:bg-emerald-950/40 text-left transition cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-emerald-400">1. Authentic Human</span>
                    <FileAudio className="w-4 h-4 text-emerald-400" />
                  </div>
                  <p className="text-[11px] text-slate-400 leading-snug">Natural formant intonation & vocal jitter (SAFE ~ 20%).</p>
                </button>

                <button
                  type="button"
                  disabled={loading}
                  onClick={() => onStartModeA('sample_human_noisy.wav')}
                  className="p-3.5 rounded-xl border border-yellow-500/30 bg-yellow-950/20 hover:bg-yellow-950/40 text-left transition cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-yellow-400">2. Noisy Human Voice</span>
                    <FileAudio className="w-4 h-4 text-yellow-400" />
                  </div>
                  <p className="text-[11px] text-slate-400 leading-snug">Tests noise stripping preventing false alarms (SAFE ~ 25%).</p>
                </button>

                <button
                  type="button"
                  disabled={loading}
                  onClick={() => onStartModeA('sample_synthetic_clone.wav')}
                  className="p-3.5 rounded-xl border border-red-500/30 bg-red-950/20 hover:bg-red-950/40 text-left transition cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-red-400">3. AI Voice Clone (TTS)</span>
                    <FileAudio className="w-4 h-4 text-red-400" />
                  </div>
                  <p className="text-[11px] text-slate-400 leading-snug">Triggers LFCC upper-band anomaly (CRITICAL &gt; 80%).</p>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content: Mode B (Live WebRTC Call) */}
        {activeTab === 'mode_b' && (
          <div className="space-y-6">
            <div className="border-2 border-dashed border-slate-700 rounded-xl p-6 text-center bg-slate-950/30">
              <PhoneCall className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
              <p className="text-xs font-semibold text-white">Browser-to-Browser Live Call</p>
              <p className="text-[11px] text-slate-400 mt-1 max-w-sm mx-auto">
                Uses WebRTC and live microphone capture. Audio is streamed to the backend in 2.5s chunks for real-time analysis.
              </p>
              
              <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => onStartModeB(null)}
                  className="py-2.5 px-6 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition shadow-lg cursor-pointer disabled:opacity-50"
                >
                  {loading ? 'Starting...' : 'Create Live Room'}
                </button>
                <span className="text-slate-500 font-bold text-xs uppercase">OR</span>
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    type="text"
                    placeholder="Enter Room Code"
                    value={roomCodeInput}
                    onChange={(e) => setRoomCodeInput(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                  />
                  <button
                    type="button"
                    disabled={loading || !roomCodeInput}
                    onClick={() => onStartModeB(roomCodeInput)}
                    className="py-2.5 px-6 rounded-xl bg-slate-700 hover:bg-slate-600 text-white font-bold text-xs uppercase tracking-wider transition cursor-pointer disabled:opacity-50"
                  >
                    Join Room
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

