import React, { useState, useEffect, useRef } from 'react';
import {
  Terminal,
  RefreshCw,
  Search,
  Download,
  FileText,
  AlertOctagon,
  Cpu
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function LogsView() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState('app'); // 'app', 'error', 'analysis'
  const [logContent, setLogContent] = useState([]);
  const [totalLines, setTotalLines] = useState(0);
  const [logStatus, setLogStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const logTerminalRef = useRef(null);

  useEffect(() => {
    fetchLogStatus();
    fetchLogs(activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchLogs(activeTab, false);
      fetchLogStatus();
    }, 3000);
    return () => clearInterval(interval);
  }, [activeTab, autoRefresh]);

  const fetchLogStatus = async () => {
    try {
      const res = await fetch('/logs/status');
      if (res.ok) {
        const data = await res.json();
        setLogStatus(data);
      }
    } catch (err) {
      console.warn('Could not fetch logs status:', err);
    }
  };

  const fetchLogs = async (fileType, showLoader = true) => {
    try {
      if (showLoader) setLoading(true);
      const res = await fetch(`/logs/recent?file_type=${fileType}&lines=200`);
      if (res.ok) {
        const data = await res.json();
        setLogContent(data.content || []);
        setTotalLines(data.total_file_lines || 0);
      }
    } catch (err) {
      console.error('Error fetching logs:', err);
    } finally {
      if (showLoader) setLoading(false);
    }
  };

  const handleDownload = () => {
    const text = logContent.join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `voice_sentry_${activeTab}_log_${Date.now()}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredLogs = logContent.filter(line => {
    if (!searchQuery) return true;
    return line.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const getLineColor = (line) => {
    if (line.includes('[ERROR]') || line.includes('CRITICAL') || line.includes('Traceback')) {
      return 'text-red-400 bg-red-950/20';
    }
    if (line.includes('[WARNING]') || line.includes('WARN')) {
      return 'text-amber-400 bg-amber-950/20';
    }
    if (line.includes('[INFO]')) {
      return 'text-slate-300';
    }
    if (line.includes('DEBUG')) {
      return 'text-slate-500';
    }
    return 'text-slate-400';
  };

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6 animate-fadeIn">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <Terminal className="w-8 h-8 text-cyan-400" />
            {t('logs_title', 'Real-Time Forensic Logs & Diagnostics')}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {t('logs_subtitle', 'Inspect low-level backend request trails, DSP mathematical evaluations, and error stack traces.')}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${
              autoRefresh
                ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-emerald-400 animate-ping' : 'bg-slate-500'}`} />
            <span>{autoRefresh ? t('logs_auto_refresh', 'Auto-Refresh (3s)') : 'Paused'}</span>
          </button>

          <button
            onClick={() => fetchLogs(activeTab, true)}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            <span>{t('logs_refresh', 'Refresh')}</span>
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 border border-cyan-700/50 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{t('logs_download', 'Download')}</span>
          </button>
        </div>
      </div>

      {/* Log File Metadata Cards */}
      {logStatus?.files && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div
            onClick={() => setActiveTab('app')}
            className={`p-4 rounded-2xl border cursor-pointer transition ${
              activeTab === 'app' ? 'bg-slate-900 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.15)]' : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-400" />
                {t('logs_app_tab', 'App & Audit Log')}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300">
                {logStatus.files.app_log?.size_kb} KB
              </span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono block mt-2 truncate">
              {logStatus.files.app_log?.path}
            </span>
          </div>

          <div
            onClick={() => setActiveTab('error')}
            className={`p-4 rounded-2xl border cursor-pointer transition ${
              activeTab === 'error' ? 'bg-slate-900 border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.15)]' : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-red-400" />
                {t('logs_error_tab', 'Error & Crash Log')}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-red-300">
                {logStatus.files.error_log?.size_kb} KB
              </span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono block mt-2 truncate">
              {logStatus.files.error_log?.path}
            </span>
          </div>

          <div
            onClick={() => setActiveTab('analysis')}
            className={`p-4 rounded-2xl border cursor-pointer transition ${
              activeTab === 'analysis' ? 'bg-slate-900 border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.15)]' : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                {t('logs_analysis_tab', 'DSP Analysis Log')}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-purple-300">
                {logStatus.files.analysis_log?.size_kb} KB
              </span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono block mt-2 truncate">
              {logStatus.files.analysis_log?.path}
            </span>
          </div>
        </div>
      )}

      {/* Terminal View Container */}
      <div className="rounded-2xl bg-slate-950 border border-slate-800 shadow-2xl overflow-hidden flex flex-col">
        {/* Terminal Header */}
        <div className="px-4 py-3 bg-slate-900/90 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-yellow-500/80 inline-block" />
              <span className="w-3 h-3 rounded-full bg-green-500/80 inline-block" />
            </div>
            <span className="text-xs font-mono text-slate-300 font-semibold">
              tail -n 200 {activeTab}.log
            </span>
            <span className="text-[11px] text-slate-500 font-mono">
              ({totalLines} lines in file)
            </span>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder={t('logs_search_placeholder', 'Filter log messages...')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 rounded-lg text-xs bg-slate-800/90 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono w-48 sm:w-64"
            />
          </div>
        </div>

        {/* Terminal Output Area */}
        <div
          ref={logTerminalRef}
          className="p-4 h-[480px] overflow-y-auto font-mono text-xs space-y-1 bg-black/40 select-text"
        >
          {filteredLogs.length > 0 ? (
            filteredLogs.map((line, idx) => (
              <div
                key={idx}
                className={`py-0.5 px-2 rounded hover:bg-slate-800/40 transition whitespace-pre-wrap break-all ${getLineColor(line)}`}
              >
                {line}
              </div>
            ))
          ) : (
            <div className="h-full flex items-center justify-center text-slate-600 font-mono text-xs">
              {t('logs_no_logs', 'No log lines recorded for this stream.')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
