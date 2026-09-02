import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Activity,
  AlertTriangle,
  FileSpreadsheet,
  Download,
  Trash2,
  Eye,
  RefreshCw,
  Search,
  Filter,
  BarChart3,
  TrendingUp,
  Cpu,
  Clock,
  CheckCircle2,
  X
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  PieChart,
  Pie
} from 'recharts';
import { useLanguage } from '../context/LanguageContext';

export default function DashboardView() {
  const { t } = useLanguage();
  const [overview, setOverview] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [contextFilter, setContextFilter] = useState('all');

  // Inspection Modal State
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [sessionSummary, setSessionSummary] = useState(null);
  const [sessionHistory, setSessionHistory] = useState([]);
  const [modalLoading, setModalLoading] = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, [riskFilter, contextFilter]);

  const fetchDashboardData = async () => {
    try {
      setRefreshing(true);
      const [overviewRes, sessionsRes] = await Promise.all([
        fetch('/analytics/overview'),
        fetch(`/analytics/sessions?limit=50&risk_level=${riskFilter}&context=${contextFilter}`)
      ]);

      if (overviewRes.ok) {
        const ovData = await overviewRes.json();
        setOverview(ovData);
      }

      if (sessionsRes.ok) {
        const sessData = await sessionsRes.json();
        setSessions(sessData.sessions || []);
      }
    } catch (err) {
      console.error('Failed to load dashboard analytics:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete session ${sessionId}?`)) return;

    try {
      const res = await fetch(`/analytics/sessions/${sessionId}`, { method: 'DELETE' });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.session_id !== sessionId));
        if (selectedSessionId === sessionId) {
          setSelectedSessionId(null);
        }
        // Refresh overview
        fetch('/analytics/overview')
          .then(r => r.json())
          .then(data => setOverview(data))
          .catch(err => console.error(err));
      }
    } catch (err) {
      console.error('Error deleting session:', err);
    }
  };

  const handleInspectSession = async (sessionId) => {
    setSelectedSessionId(sessionId);
    setModalLoading(true);
    try {
      const [sumRes, histRes] = await Promise.all([
        fetch(`/calls/${sessionId}/summary`),
        fetch(`/calls/${sessionId}/history`)
      ]);

      if (sumRes.ok) {
        const sumData = await sumRes.json();
        setSessionSummary(sumData);
      }
      if (histRes.ok) {
        const histData = await histRes.json();
        setSessionHistory(histData.history || []);
      }
    } catch (err) {
      console.error('Failed to inspect session:', err);
    } finally {
      setModalLoading(false);
    }
  };

  const handleExport = (format) => {
    window.open(`/analytics/export?format=${format}`, '_blank');
  };

  // Filter sessions by search query client-side
  const filteredSessions = sessions.filter(s => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      s.session_id?.toLowerCase().includes(query) ||
      s.transaction_context?.toLowerCase().includes(query) ||
      s.mode?.toLowerCase().includes(query)
    );
  });

  const getRiskBadge = (peakRisk) => {
    if (peakRisk >= 70) {
      return { label: 'CRITICAL', color: 'bg-red-500/20 text-red-400 border-red-500/40' };
    }
    if (peakRisk >= 40) {
      return { label: 'WARNING', color: 'bg-amber-500/20 text-amber-400 border-amber-500/40' };
    }
    return { label: 'NORMAL', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' };
  };

  const CONTEXT_COLORS = {
    fund_transfer: '#ef4444',
    otp_share: '#f97316',
    credential_reset: '#eab308',
    general: '#10b981'
  };

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6 animate-fadeIn">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-cyan-400" />
            {t('dash_title', 'Security Telemetry & Threat Dashboard')}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {t('dash_subtitle', 'Aggregated intelligence on intercepted synthetic voice calls and acoustic risk distributions.')}
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={fetchDashboardData}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/80 hover:border-slate-600 transition shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => handleExport('csv')}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 border border-cyan-700/50 transition shadow-sm"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>{t('dash_btn_export_csv', 'Export CSV')}</span>
          </button>

          <button
            onClick={() => handleExport('json')}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/80 transition shadow-sm"
          >
            <Download className="w-3.5 h-3.5 text-blue-400" />
            <span>{t('dash_btn_export_json', 'Export JSON')}</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Scanned */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-semibold uppercase text-slate-400 tracking-wider">
              {t('dash_total_scanned', 'Total Calls Analyzed')}
            </span>
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-white font-mono">
              {overview?.total_sessions ?? 0}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({overview?.total_audio_chunks ?? 0} chunks)
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Real-time DSP + AASIST</span>
          </div>
        </div>

        {/* Card 2: Threat Rate */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-semibold uppercase text-slate-400 tracking-wider">
              {t('dash_threat_rate', 'Threat Interception Rate')}
            </span>
            <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-red-400 font-mono">
              {overview?.threat_interception_rate ?? 0}%
            </span>
            <span className="text-xs text-red-300 font-mono">
              ({overview?.critical_alerts ?? 0} critical)
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span>{overview?.warning_alerts ?? 0} warning escalations</span>
          </div>
        </div>

        {/* Card 3: Avg Risk Score */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-semibold uppercase text-slate-400 tracking-wider">
              {t('dash_avg_risk', 'System Average Risk')}
            </span>
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-amber-300 font-mono">
              {overview?.overall_avg_risk ?? 0}%
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Peak: {overview?.overall_peak_risk ?? 0}%
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span>EWMA Smoothing (α=0.35)</span>
          </div>
        </div>

        {/* Card 4: Processing Latency */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md relative overflow-hidden shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-semibold uppercase text-slate-400 tracking-wider">
              {t('dash_processing_latency', 'Processing Latency')}
            </span>
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-emerald-400 font-mono">
              &lt; 25 ms
            </span>
            <span className="text-xs text-slate-400 font-mono">
              / 2.5s chunk
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            <span>100x Real-time speed</span>
          </div>
        </div>
      </div>

      {/* Visual Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Area Chart */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md flex flex-col justify-between shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                {t('dash_risk_trend_title', 'Risk Level Evolution & Daily Call Volume')}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Average and peak risk levels across analyzed audio sessions.</p>
            </div>
          </div>

          <div className="h-64 w-full">
            {overview?.daily_trends && overview.daily_trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={overview.daily_trends}>
                  <defs>
                    <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="maxGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="day" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                    labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
                  />
                  <Area type="monotone" dataKey="avg_risk" name="Avg Risk %" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#riskGrad)" />
                  <Area type="monotone" dataKey="max_risk" name="Peak Risk %" stroke="#ef4444" strokeWidth={2} strokeDasharray="4 4" fillOpacity={1} fill="url(#maxGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm font-mono">
                Awaiting more call sessions to plot historical timeline trends.
              </div>
            )}
          </div>
        </div>

        {/* Threat Distribution by Context */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md flex flex-col justify-between shadow-lg">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-red-400" />
              {t('dash_context_breakdown_title', 'Threat Distribution by Context')}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Vulnerability index across transaction types.</p>
          </div>

          <div className="h-56 w-full my-auto flex items-center justify-center">
            {overview?.context_breakdown && overview.context_breakdown.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overview.context_breakdown} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis type="number" stroke="#64748b" fontSize={11} domain={[0, 100]} />
                  <YAxis type="category" dataKey="transaction_context" stroke="#64748b" fontSize={10} width={90} tickFormatter={(val) => val.replace('_', ' ').toUpperCase()} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                  />
                  <Bar dataKey="avg_peak_risk" name="Avg Peak Risk %" radius={[0, 8, 8, 0]}>
                    {overview.context_breakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CONTEXT_COLORS[entry.transaction_context] || '#06b6d4'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-slate-500 text-xs font-mono text-center">
                No context data available.
              </div>
            )}
          </div>

          {/* Context legend pills */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/60 text-[10px] font-mono">
            <div className="flex items-center gap-1.5 text-red-400">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span>Fund Transfer</span>
            </div>
            <div className="flex items-center gap-1.5 text-orange-400">
              <span className="w-2 h-2 rounded-full bg-orange-500" />
              <span>OTP Disclosure</span>
            </div>
            <div className="flex items-center gap-1.5 text-yellow-400">
              <span className="w-2 h-2 rounded-full bg-yellow-500" />
              <span>Credential Reset</span>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>General Chat</span>
            </div>
          </div>
        </div>
      </div>

      {/* Historical Sessions Table */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md shadow-lg space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              {t('dash_recent_sessions', 'Recent Call Sessions & Incidents')}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Browse past calls, examine forensic acoustic metrics, or delete test logs.</p>
          </div>

          {/* Search & Filters */}
          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder={t('dash_search_placeholder', 'Search session ID or context...')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-xl text-xs bg-slate-800/80 border border-slate-700/80 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/80 w-48 sm:w-56"
              />
            </div>

            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="px-3 py-1.5 rounded-xl text-xs bg-slate-800/80 border border-slate-700/80 text-slate-200 focus:outline-none focus:border-cyan-500/80 font-mono"
            >
              <option value="all">{t('dash_filter_all_risk', 'All Risk Levels')}</option>
              <option value="high">{t('dash_filter_high_risk', 'High Risk (>70%)')}</option>
              <option value="medium">{t('dash_filter_med_risk', 'Medium Risk (40-70%)')}</option>
              <option value="low">{t('dash_filter_low_risk', 'Low Risk (<40%)')}</option>
            </select>

            <select
              value={contextFilter}
              onChange={(e) => setContextFilter(e.target.value)}
              className="px-3 py-1.5 rounded-xl text-xs bg-slate-800/80 border border-slate-700/80 text-slate-200 focus:outline-none focus:border-cyan-500/80 font-mono"
            >
              <option value="all">{t('dash_filter_all_ctx', 'All Contexts')}</option>
              <option value="fund_transfer">Fund Transfer</option>
              <option value="otp_share">OTP Share</option>
              <option value="credential_reset">Credential Reset</option>
              <option value="general">General</option>
            </select>
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-mono border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">{t('dash_col_session', 'Session ID')}</th>
                <th className="py-3 px-4">{t('dash_col_mode', 'Mode')}</th>
                <th className="py-3 px-4">{t('dash_col_context', 'Context')}</th>
                <th className="py-3 px-4">{t('dash_col_peak', 'Peak Risk')}</th>
                <th className="py-3 px-4">{t('dash_col_avg', 'Avg Risk')}</th>
                <th className="py-3 px-4">{t('dash_col_chunks', 'Chunks')}</th>
                <th className="py-3 px-4">{t('dash_col_time', 'Date / Time')}</th>
                <th className="py-3 px-4 text-right">{t('dash_col_actions', 'Actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredSessions.length > 0 ? (
                filteredSessions.map((s) => {
                  const badge = getRiskBadge(s.peak_risk || 0);
                  const dateStr = s.created_at
                    ? new Date(s.created_at * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : 'N/A';

                  return (
                    <tr
                      key={s.session_id}
                      onClick={() => handleInspectSession(s.session_id)}
                      className="hover:bg-slate-800/40 cursor-pointer transition"
                    >
                      <td className="py-3 px-4 text-slate-200 font-bold flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] border ${badge.color}`}>
                          {badge.label}
                        </span>
                        <span className="truncate max-w-[140px]">{s.session_id}</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {s.mode === 'mode_b_live' ? (
                          <span className="text-cyan-400 font-semibold">LIVE WEBRTC</span>
                        ) : (
                          <span className="text-purple-400">UPLOAD REPLAY</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px]">
                          {s.transaction_context?.replace('_', ' ').toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-800 h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${s.peak_risk >= 70 ? 'bg-red-500' : s.peak_risk >= 40 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                              style={{ width: `${Math.min(100, s.peak_risk || 0)}%` }}
                            />
                          </div>
                          <span className="font-bold text-white">{s.peak_risk ?? 0}%</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-semibold">
                        {s.avg_risk ?? 0}%
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {s.total_chunks ?? 0}
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {dateStr}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => handleInspectSession(s.session_id)}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 transition"
                            title="Inspect Session"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => handleDeleteSession(s.session_id, e)}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-red-950 text-slate-400 hover:text-red-400 transition"
                            title="Delete Session"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 font-mono">
                    {t('dash_no_sessions', 'No call sessions found matching your filter criteria.')}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forensic Inspection Modal */}
      {selectedSessionId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-2xl animate-scaleUp">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-cyan-400" />
                  {t('dash_modal_title', 'Forensic Session Telemetry')}
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">Session: {selectedSessionId}</p>
              </div>
              <button
                onClick={() => setSelectedSessionId(null)}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {modalLoading ? (
              <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400 font-mono text-xs">
                <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
                <span>Loading forensic telemetry...</span>
              </div>
            ) : (
              <>
                {/* Session Summary Header */}
                {sessionSummary && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
                      <span className="text-slate-500 block font-mono">MODE</span>
                      <span className="font-bold text-white font-mono">{sessionSummary.mode}</span>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
                      <span className="text-slate-500 block font-mono">CONTEXT</span>
                      <span className="font-bold text-cyan-300 font-mono">{sessionSummary.transaction_context}</span>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
                      <span className="text-slate-500 block font-mono">PEAK RISK</span>
                      <span className={`font-bold font-mono ${sessionSummary.peak_risk >= 70 ? 'text-red-400' : 'text-emerald-400'}`}>
                        {sessionSummary.peak_risk}%
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
                      <span className="text-slate-500 block font-mono">AVG RISK</span>
                      <span className="font-bold text-amber-300 font-mono">{sessionSummary.avg_risk}%</span>
                    </div>
                  </div>
                )}

                {/* Risk Progression Timeline */}
                {sessionHistory.length > 0 && (
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                    <span className="text-xs font-bold text-slate-300 font-mono uppercase tracking-wider block">
                      Chunk-by-Chunk Risk Score Progression
                    </span>
                    <div className="h-48 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={sessionHistory}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="chunk_index" stroke="#64748b" fontSize={10} />
                          <YAxis stroke="#64748b" fontSize={10} domain={[0, 100]} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem', fontSize: '11px' }}
                          />
                          <Area type="monotone" dataKey="rolling_risk_score" name="Rolling Risk %" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.2} />
                          <Area type="monotone" dataKey="chunk_risk_score" name="Raw Chunk Risk %" stroke="#ef4444" fill="transparent" strokeDasharray="3 3" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Triggered Alerts History */}
                {sessionSummary?.alerts && sessionSummary.alerts.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-bold text-red-400 font-mono uppercase tracking-wider block">
                      Triggered Security Alerts ({sessionSummary.alerts.length})
                    </span>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {sessionSummary.alerts.map((al, idx) => (
                        <div key={idx} className="p-3 rounded-xl bg-red-950/40 border border-red-500/40 text-xs text-red-300 flex items-start gap-2.5">
                          <ShieldAlert className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                          <div className="flex-1 min-w-0 font-mono">
                            <div className="flex items-center justify-between">
                              <span className="font-bold">{al.severity} ALERT ({al.risk_score}%)</span>
                              <span className="text-[10px] text-red-400/70">Chunk #{al.chunk_index}</span>
                            </div>
                            <p className="text-[11px] text-slate-300 mt-1">{al.recommended_action}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
