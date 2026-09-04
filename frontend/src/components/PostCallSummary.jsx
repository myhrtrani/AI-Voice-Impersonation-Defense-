import React from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  AlertTriangle, 
  Clock, 
  Activity, 
  Layers, 
  RotateCcw, 
  DownloadCloud,
  FileCheck2,
  Lock
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  ReferenceLine 
} from 'recharts';

export default function PostCallSummary({ summaryData, historyData = [], onReset, thresholds }) {
  const peakRisk = summaryData?.peak_risk ?? (historyData.length > 0 ? Math.max(...historyData.map(h => h.rolling_risk_score || 0)) : 0);
  const avgRisk = summaryData?.avg_risk ?? (historyData.length > 0 ? (historyData.reduce((acc, h) => acc + (h.rolling_risk_score || 0), 0) / historyData.length) : 0);
  const totalChunks = summaryData?.total_chunks || historyData.length;
  const alerts = summaryData?.alerts || [];
  const durationSec = totalChunks * 2.5;

  const highMin = thresholds?.high_min || 60;
  const lowMax = thresholds?.low_max || 40;

  const humanRatio = summaryData?.human_ratio ?? 100;
  const aiRatio = summaryData?.ai_ratio ?? 0;

  // Final verdict uses the backend multi-chunk classification and thresholds.
  const isGenuineHuman = summaryData?.verdict === 'GENUINE_HUMAN' || (humanRatio >= 65.0 && aiRatio < 35.0 && peakRisk < highMin);
  const isHighRisk = !isGenuineHuman && (summaryData?.verdict === 'FULL_AI_CALL' || summaryData?.verdict === 'TARGETED_AI_INJECTION' || peakRisk >= highMin || aiRatio >= 35.0);
  const isMediumRisk = !isGenuineHuman && !isHighRisk && (summaryData?.verdict === 'SUSPICIOUS_CALL' || peakRisk >= 55 || humanRatio < 60.0);
  const verdictTitle = summaryData?.verdict_label || (isGenuineHuman ? 'Authentic Human Call Verified' : isHighRisk ? 'Critical Voice Impersonation Detected' : 'Voice Impersonation Warning');

  const chartData = historyData.map((d) => ({
    time: `${d.elapsed_seconds || (d.chunk_index * 2.5)}s`,
    risk: d.rolling_risk_score
  }));

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      {/* Header Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 lg:p-8 shadow-2xl backdrop-blur-md">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-6 mb-6">
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-xl border ${
              isHighRisk
                ? 'bg-red-950/40 border-red-500/50 text-red-400'
                : isMediumRisk
                  ? 'bg-amber-950/40 border-amber-500/50 text-amber-400'
                  : 'bg-emerald-950/40 border-emerald-500/50 text-emerald-400'
            }`}>
              {isHighRisk ? (
                <ShieldAlert size={24} />
              ) : isMediumRisk ? (
                <AlertTriangle size={24} />
              ) : (
                <ShieldCheck size={24} />
              )}
            </div>

            <div>
              <h2 className="text-xl font-bold text-white">
                {verdictTitle}
              </h2>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Authenticity: <span className="text-emerald-400 font-semibold">{humanRatio}% Human</span>
                {aiRatio > 0 && <span className="text-red-400 font-semibold ml-2">• {aiRatio}% AI Detected</span>}
              </p>
            </div>
          </div>
<button
            onClick={onReset}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs uppercase tracking-wider transition shadow-lg cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Start New Session</span>
          </button>
        </div>

        {/* Aggregate KPI Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[11px] font-mono text-slate-400">Peak Sustained Risk</span>
            <div className={`text-2xl font-black font-mono mt-1 ${isHighRisk ? 'text-red-400' : 'text-emerald-400'}`}>
              {Math.round(peakRisk)}%
            </div>
            <span className="text-[10px] text-slate-500">Threshold: {highMin}%</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[11px] font-mono text-slate-400">Average Risk Score</span>
            <div className="text-2xl font-black font-mono text-white mt-1">
              {Math.round(avgRisk)}%
            </div>
            <span className="text-[10px] text-slate-500">Call-wide mean</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[11px] font-mono text-slate-400">Call Duration</span>
            <div className="text-2xl font-black font-mono text-cyan-400 mt-1">
              {durationSec.toFixed(1)}s
            </div>
            <span className="text-[10px] text-slate-500">{totalChunks} Analyzed Chunks</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[11px] font-mono text-slate-400">Security Alerts</span>
            <div className={`text-2xl font-black font-mono mt-1 ${alerts.length > 0 ? 'text-red-400' : 'text-slate-400'}`}>
              {alerts.length}
            </div>
            <span className="text-[10px] text-slate-500">Escalated warnings</span>
          </div>
        </div>
      </div>

      {/* Full Session Risk Timeline Chart */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-md">
        <h3 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <span>Full Call Risk Trajectory</span>
        </h3>
        <p className="text-xs text-slate-400 font-mono mb-4">Complete 0-100 risk timeline across total duration</p>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
              <YAxis domain={[0, 100]} stroke="#64748b" fontSize={11} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                itemStyle={{ color: '#e2e8f0' }}
              />
              <ReferenceLine y={highMin} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'CRITICAL', fill: '#ef4444', fontSize: 10 }} />
              <ReferenceLine y={55} stroke="#eab308" strokeDasharray="4 4" label={{ value: 'WARN', fill: '#eab308', fontSize: 10 }} />
              <Line type="monotone" dataKey="risk" stroke="#06b6d4" strokeWidth={3} dot={{ r: 3, fill: '#06b6d4' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Alerts Log Table */}
      {alerts.length > 0 && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-md">
          <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-red-400" />
            <span>Triggered Fraud Alerts Log ({alerts.length})</span>
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400 font-mono">
                <tr>
                  <th className="py-2 px-3">Chunk #</th>
                  <th className="py-2 px-3">Severity</th>
                  <th className="py-2 px-3">Risk Score</th>
                  <th className="py-2 px-3">Recommended Security Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {alerts.map((al, idx) => (
                  <tr key={idx} className="hover:bg-slate-950/40">
                    <td className="py-2.5 px-3">Chunk #{al.chunk_index}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${al.severity === 'CRITICAL' ? 'bg-red-950 text-red-400 border border-red-800' : 'bg-yellow-950 text-yellow-400 border border-yellow-800'}`}>
                        {al.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-bold text-white">{Math.round(al.risk_score)}%</td>
                    <td className="py-2.5 px-3 font-sans text-xs text-slate-200">{al.recommended_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}




