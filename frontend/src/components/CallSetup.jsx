import React, { useState } from 'react';
import {
  PhoneCall,
  UploadCloud,
  ShieldAlert,
  FileAudio,
  Play,
  Radio,
  Zap,
  ChevronDown
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



  const handleFileUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      {/* Hero Title */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-400 text-xs font-mono mb-3">
          <Zap className="w-3.5 h-3.5" />
          <span>REAL-TIME MULTI-BAND ACOUSTIC INFERENCE</span>
        </div>
        <h2 className="text-3xl lg:text-4xl font-extrabold text-white tracking-tight">
          AI Voice Impersonation Defense
        </h2>
        <p className="text-slate-400 text-sm max-w-xl mx-auto mt-2">
          Continuously evaluates conversational audio stream in 2.5s chunks. Detects neural
          vocoder phase ripple, LFCC spectral anomalies, and synthetic pitch flatness.
          CRITICAL threshold: <span className="text-cyan-400 font-bold">60%</span> for all contexts.
        </p>
      </div>

      {/* Unified Detection Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden">

        {/* Card Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-800 bg-slate-950/40">
          <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-500/30">
            <ShieldAlert className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">AI Voice Impersonation Detection</h3>
            <p className="text-[11px] font-mono text-slate-400 mt-0.5">
              AASIST-L · LFCC · Pitch Jitter · Spectral Analysis · CRITICAL ≥ 60%
            </p>
          </div>
        </div>

        <div className="p-6 space-y-6">



          {/* Mode Tabs */}
          <div className="flex gap-1 bg-slate-950/60 rounded-xl p-1 border border-slate-800">
            <button
              onClick={() => setActiveTab('mode_a')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                activeTab === 'mode_a'
                  ? 'bg-cyan-500 text-slate-950 shadow-lg'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Radio className="w-3.5 h-3.5" />
              Mode A — Replay
            </button>
            <button
              onClick={() => setActiveTab('mode_b')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                activeTab === 'mode_b'
                  ? 'bg-cyan-500 text-slate-950 shadow-lg'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <PhoneCall className="w-3.5 h-3.5" />
              Mode B — Live
            </button>
          </div>

          {/* Mode A Content */}
          {activeTab === 'mode_a' && (
            <div className="space-y-5">
              <div className="border-2 border-dashed border-slate-700 hover:border-cyan-500/50 rounded-xl p-6 text-center bg-slate-950/30 transition">
                <UploadCloud className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
                <p className="text-xs font-semibold text-white">Upload Call Audio File (.wav, .mp3, .ogg)</p>
                <p className="text-[11px] text-slate-400 mt-1">Backend simulates real-time live streaming playback</p>

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

              {/* Demo Presets */}
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
                    <p className="text-[11px] text-slate-400 leading-snug">Natural formant intonation &amp; vocal jitter (SAFE ~ 20%).</p>
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
                    <p className="text-[11px] text-slate-400 leading-snug">Triggers LFCC upper-band anomaly (CRITICAL &gt; 60%).</p>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Mode B Content */}
          {activeTab === 'mode_b' && (
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
          )}

        </div>
      </div>
    </div>
  );
}
