import React from 'react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ReferenceLine, 
  CartesianGrid 
} from 'recharts';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Cpu, 
  Activity, 
  PhoneOff, 
  Radio, 
  Sliders, 
  CheckCircle, 
  Zap,
  Volume2
} from 'lucide-react';

export default function LiveDashboard({
  sessionId,
  mode,
  transactionContext,
  onChangeContext,
  onEndCall,
  liveMetrics,
  historyData,
  thresholds
}) {
  const currentRollingRisk = liveMetrics?.rolling_risk_score ?? 0;
  const currentChunkRisk = liveMetrics?.chunk_risk_score ?? 0;
  const severity = liveMetrics?.severity || 'NORMAL';
  const alertFired = liveMetrics?.alert_fired;
  const recommendedAction = liveMetrics?.recommended_action;
  const noiseStripped = liveMetrics?.noise_stripped ?? true;
  const features = liveMetrics?.features || {};

  // Status color logic based on config thresholds (used for chart ReferenceLines)
  const lowMax = thresholds?.low_max || 40;
  const highMin = thresholds?.high_min || 70;

  // Use the backend-provided severity rather than recalculating it on the frontend
  const getRiskStatus = (backendSeverity) => {
    if (backendSeverity === 'CRITICAL') {
      return {
        label: 'CRITICAL RISK: SYNTHETIC / CLONED VOICE',
        badge: 'CRITICAL',
        color: 'text-red-400',
        bg: 'bg-red-950/40',
        border: 'border-red-500/60',
        ring: 'ring-red-500/40',
        barColor: 'from-red-500 to-rose-600',
        icon: ShieldAlert
      };
    }
    if (backendSeverity === 'WARNING') {
      return {
        label: 'ELEVATED SUSPICION: ANOMALIES DETECTED',
        badge: 'SUSPICIOUS',
        color: 'text-yellow-400',
        bg: 'bg-yellow-950/40',
        border: 'border-yellow-500/60',
        ring: 'ring-yellow-500/40',
        barColor: 'from-yellow-500 to-amber-600',
        icon: AlertTriangle
      };
    }
    return {
      label: 'AUTHENTIC HUMAN SPEECH VERIFIED',
      badge: 'SAFE',
      color: 'text-emerald-400',
      bg: 'bg-emerald-950/40',
      border: 'border-emerald-500/60',
      ring: 'ring-emerald-500/40',
      barColor: 'from-emerald-400 to-teal-500',
      icon: ShieldCheck
    };
  };

  const status = getRiskStatus(severity);
  const StatusIcon = status.icon;

  // Chart data format
  const chartData = historyData.map((d) => ({
    time: `${d.elapsed_seconds || (d.chunk_index * 2.5)}s`,
    chunkRisk: d.chunk_risk_score,
    rollingRisk: d.rolling_risk_score
  }));

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 space-y-6">
      {/* Top Stream Control Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/90 border border-slate-800 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                Mode A Stream Replay
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                ID: {sessionId}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono mt-0.5">
              Elapsed: {liveMetrics?.elapsed_seconds || 0}s | Analyzed Chunks: {historyData.length}
            </p>
          </div>
        </div>

        {/* Dynamic Context Switcher & End Call */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400 font-mono">Context:</span>
            <select
              value={transactionContext}
              onChange={(e) => onChangeContext(e.target.value)}
              className="bg-transparent text-xs font-semibold text-cyan-300 focus:outline-none cursor-pointer"
            >
              <option value="general" className="bg-slate-900 text-white">General (Normal)</option>
              <option value="credential_reset" className="bg-slate-900 text-white">Credential Reset (&gt;60%)</option>
              <option value="otp_share" className="bg-slate-900 text-white">OTP Disclosure (&gt;50%)</option>
              <option value="fund_transfer" className="bg-slate-900 text-white">Fund Transfer (&gt;45%)</option>
            </select>
          </div>

          <button
            onClick={onEndCall}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition shadow-[0_0_15px_rgba(239,68,68,0.3)] cursor-pointer"
          >
            <PhoneOff className="w-4 h-4" />
            <span>End Call</span>
          </button>
        </div>
      </div>

      {/* Emergency Action Banner (When Severity is WARNING or CRITICAL) */}
      {severity !== 'NORMAL' && (
        <div className={`p-4 rounded-xl border ${status.border} ${status.bg} shadow-lg transition-all animate-pulse-fast`}>
          <div className="flex items-start gap-3">
            <StatusIcon className={`w-6 h-6 ${status.color} shrink-0 mt-0.5`} />
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h3 className={`text-sm font-extrabold tracking-wide uppercase ${status.color}`}>
                  SECURITY ALERT: {severity} RISK LEVEL
                </h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-900 text-white">
                  ACTION REQUIRED
                </span>
              </div>
              <p className="text-xs font-semibold text-slate-200 mt-1 leading-relaxed">
                {recommendedAction}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid: Live Gauge & Rolling Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Risk Gauge & Status Meter (5 cols) */}
        <div className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-mono uppercase tracking-widest text-slate-400">
                Synthetic Speech Risk Score
              </span>
              <span className={`text-[10px] font-bold tracking-widest px-2.5 py-0.5 rounded-full border ${status.border} ${status.color} bg-slate-950`}>
                {status.badge}
              </span>
            </div>

            {/* Circular / Large Numeric Gauge */}
            <div className="my-6 text-center">
              <div className="relative inline-flex items-center justify-center">
                {/* Outer Glow Ring */}
                <div className={`w-48 h-48 rounded-full border-8 ${status.border} ${status.bg} flex flex-col items-center justify-center shadow-[0_0_40px_rgba(0,0,0,0.5)]`}>
                  <span className="text-5xl font-black tracking-tighter text-white font-mono">
                    {Math.round(currentRollingRisk)}
                  </span>
                  <span className="text-[11px] font-mono text-slate-400 mt-1 uppercase tracking-wider">
                    / 100 RISK INDEX
                  </span>
                  <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                    Chunk: {Math.round(currentChunkRisk)}%
                  </div>
                </div>
              </div>
              <p className={`text-xs font-bold mt-4 tracking-wide ${status.color}`}>
                {status.label}
              </p>
            </div>
          </div>

          {/* Calibrated Risk Scale Bar */}
          <div className="space-y-2 pt-4 border-t border-slate-800/80">
            <div className="flex justify-between text-[10px] font-mono text-slate-400">
              <span>0 (Safe)</span>
              <span>40 (Suspicious)</span>
              <span>70+ (Critical)</span>
            </div>
            <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden flex border border-slate-800">
              <div className="w-[40%] bg-emerald-500/40 h-full"></div>
              <div className="w-[30%] bg-yellow-500/40 h-full"></div>
              <div className="w-[30%] bg-red-500/40 h-full"></div>
            </div>
          </div>
        </div>

        {/* Right Column: Rolling Risk Chart (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <span>Continuous Call Risk Trendline</span>
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Exponentially Weighted Moving Average (EWMA &alpha;=0.35)
                </p>
              </div>
              <div className="flex items-center gap-3 text-[11px] font-mono">
                <span className="flex items-center gap-1 text-cyan-400">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block"></span> Rolling Score
                </span>
                <span className="flex items-center gap-1 text-slate-400">
                  <span className="w-2.5 h-2.5 rounded-full bg-slate-500 inline-block"></span> Chunk Score
                </span>
              </div>
            </div>

            {/* Recharts Rolling Line Chart */}
            <div className="h-64 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
                  <YAxis domain={[0, 100]} stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                    itemStyle={{ color: '#e2e8f0' }}
                  />
                  {/* Threshold Reference Lines */}
                  <ReferenceLine y={highMin} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'CRITICAL', fill: '#ef4444', fontSize: 10, position: 'right' }} />
                  <ReferenceLine y={lowMax} stroke="#eab308" strokeDasharray="4 4" label={{ value: 'WARN', fill: '#eab308', fontSize: 10, position: 'right' }} />
                  
                  <Line type="monotone" dataKey="chunkRisk" stroke="#64748b" strokeWidth={1.5} dot={false} strokeDasharray="2 2" />
                  <Line type="monotone" dataKey="rollingRisk" stroke="#06b6d4" strokeWidth={3} dot={{ r: 3, fill: '#06b6d4' }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="text-[11px] font-mono text-slate-500 flex justify-between pt-3 border-t border-slate-800">
            <span>Threshold automatically shifts for "{transactionContext}" context</span>
            <span>Real-Time Ingestion: 16kHz Mono</span>
          </div>
        </div>
      </div>

      {/* DSP & LFCC Feature Telemetry Card (For Transparency & Judge Demo) */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>Real-Time Acoustic & LFCC Telemetry Readout</span>
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Live mathematical parameters extracted from noise-stripped 2.5s window
            </p>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-emerald-400">
            Noise Stripping: {noiseStripped ? 'ACTIVE (Spectral Gating)' : 'OFF'}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
          {/* 1. LFCC High-Band Artifact (Headline Feature) */}
          <div className="p-3.5 rounded-xl bg-cyan-950/30 border border-cyan-500/40 relative overflow-hidden">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-mono uppercase font-bold text-cyan-300">LFCC Artifact</span>
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {features.lfcc_artifact_score !== undefined ? `${features.lfcc_artifact_score}%` : '--'}
            </div>
            <p className="text-[10px] text-cyan-200/70 mt-1 leading-tight">
              Upper 4.8-8kHz vocoder phase ripple
            </p>
          </div>

          {/* 2. Pitch Variance */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] font-mono uppercase text-slate-400">Pitch Variance</span>
            <div className="text-xl font-bold font-mono text-white mt-1">
              {features.pitch_variance !== undefined ? features.pitch_variance : '--'}
            </div>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">
              Human: &gt;100 | Flat AI: &lt;25
            </p>
          </div>

          {/* 3. Cycle-to-Cycle Jitter */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] font-mono uppercase text-slate-400">Vocal Jitter</span>
            <div className="text-xl font-bold font-mono text-white mt-1">
              {features.jitter !== undefined ? `${features.jitter}%` : '--'}
            </div>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">
              Human vocal fold: 0.5 - 1.5%
            </p>
          </div>

          {/* 4. Spectral Flatness */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] font-mono uppercase text-slate-400">Spectral Flatness</span>
            <div className="text-xl font-bold font-mono text-white mt-1">
              {features.spectral_flatness !== undefined ? features.spectral_flatness : '--'}
            </div>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">
              Tonality vs vocoder hiss
            </p>
          </div>

          {/* 5. Spectral Centroid */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] font-mono uppercase text-slate-400">Spectral Centroid</span>
            <div className="text-xl font-bold font-mono text-white mt-1">
              {features.spectral_centroid !== undefined ? `${Math.round(features.spectral_centroid)} Hz` : '--'}
            </div>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">
              Spectral brightness center
            </p>
          </div>

          {/* 6. Model Classifier Score */}
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] font-mono uppercase text-slate-400">Model Classifier</span>
            <div className="text-xl font-bold font-mono text-white mt-1">
              {features.model_score !== undefined ? `${features.model_score}%` : '--'}
            </div>
            <p className="text-[10px] text-slate-500 mt-1 leading-tight">
              Neural acoustic detector
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
