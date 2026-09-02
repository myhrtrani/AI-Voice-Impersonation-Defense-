import React, { useState } from 'react';
import {
  ShieldAlert,
  LayoutDashboard,
  Sliders,
  Languages,
  Terminal,
  ChevronLeft,
  ChevronRight,
  Radio,
  Cpu,
  Menu,
  X,
  Volume2,
  Activity
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function Sidebar({
  activePage,
  onNavigate,
  isLiveActive,
  liveMetrics
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const { t, language } = useLanguage();

  const navItems = [
    {
      id: 'live_sentry',
      label: t('nav_live_sentry', 'Live Sentry'),
      icon: Radio,
      badge: isLiveActive ? 'LIVE' : null,
      badgeColor: 'bg-red-500 text-white animate-pulse'
    },
    {
      id: 'dashboard',
      label: t('nav_dashboard', 'Dashboard'),
      icon: LayoutDashboard,
      badge: null
    },
    {
      id: 'settings',
      label: t('nav_settings', 'Settings'),
      icon: Sliders,
      badge: null
    },
    {
      id: 'language',
      label: t('nav_language', 'Language'),
      icon: Languages,
      badge: language.toUpperCase(),
      badgeColor: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
    },
    {
      id: 'logs',
      label: t('nav_logs', 'Forensic Logs'),
      icon: Terminal,
      badge: null
    }
  ];

  const handleItemClick = (pageId) => {
    onNavigate(pageId);
    setIsMobileOpen(false);
  };

  return (
    <>
      {/* Mobile Toggle Button */}
      <div className="lg:hidden fixed top-3 left-4 z-50">
        <button
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-700/80 text-cyan-400 backdrop-blur-md shadow-lg shadow-black/40 hover:bg-slate-800 transition"
          aria-label="Toggle navigation menu"
        >
          {isMobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40 transition-opacity"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`
          fixed lg:static top-0 bottom-0 left-0 z-40
          flex flex-col justify-between
          bg-slate-900/90 backdrop-blur-xl border-r border-slate-800/80
          transition-all duration-300 ease-in-out select-none
          ${isCollapsed ? 'w-20' : 'w-64'}
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          shadow-2xl shadow-black/60
        `}
      >
        {/* Brand & Logo Section */}
        <div>
          <div className={`p-4 border-b border-slate-800/80 flex items-center ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/40 text-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.3)] shrink-0">
                <ShieldAlert className="w-6 h-6 animate-pulse" />
              </div>
              {!isCollapsed && (
                <div className="flex flex-col min-w-0">
                  <span className="font-extrabold tracking-wider text-white text-base leading-tight flex items-center gap-1.5">
                    VOICE SENTRY <span className="text-cyan-400 text-xs font-black px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-600/40">AI</span>
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono tracking-tight truncate">
                    Enterprise Impersonation Shield
                  </span>
                </div>
              )}
            </div>

            {/* Desktop Collapse / Expand Toggle */}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition border border-transparent hover:border-slate-700"
              title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            >
              {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => handleItemClick(item.id)}
                  className={`
                    w-full flex items-center gap-3.5 px-3.5 py-3 rounded-xl text-sm font-medium transition-all duration-200 group relative
                    ${isActive
                      ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-cyan-300 border border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.15)] font-semibold'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 border border-transparent hover:border-slate-700/50'
                    }
                    ${isCollapsed ? 'justify-center px-2' : ''}
                  `}
                  title={isCollapsed ? item.label : undefined}
                >
                  {/* Active Indicator Strip */}
                  {isActive && (
                    <div className="absolute left-0 top-2 bottom-2 w-1 bg-cyan-400 rounded-r-full shadow-[0_0_8px_#22d3ee]" />
                  )}

                  <Icon className={`w-5 h-5 shrink-0 transition-transform group-hover:scale-110 ${isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-slate-200'}`} />

                  {!isCollapsed && (
                    <div className="flex-1 flex items-center justify-between min-w-0">
                      <span className="truncate">{item.label}</span>
                      {item.badge && (
                        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${item.badgeColor || 'bg-slate-800 text-slate-300'}`}>
                          {item.badge}
                        </span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer: System Status & Live Pulse */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
          {/* Live Call Telemetry Quick Widget if Live Sentry is streaming in background */}
          {isLiveActive && liveMetrics && !isCollapsed && (
            <div className="mb-3 p-2.5 rounded-xl bg-red-950/40 border border-red-500/40 text-xs text-red-300 animate-pulse">
              <div className="flex items-center justify-between font-mono font-bold mb-1">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                  ACTIVE SCAN
                </span>
                <span>{liveMetrics.rolling_risk_score ?? 0}% RISK</span>
              </div>
              <p className="text-[10px] text-red-400/80 truncate">
                {liveMetrics.severity || 'SCANNING CHUNKS...'}
              </p>
            </div>
          )}

          {!isCollapsed ? (
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between px-2 text-slate-400 font-mono text-[11px]">
                <span className="flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  {t('nav_status_online', 'ONLINE')}
                </span>
                <span className="text-slate-500">16kHz DSP</span>
              </div>
              <div className="px-2 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-between text-[10px] text-slate-300 font-mono">
                <span className="flex items-center gap-1 text-slate-400">
                  <Cpu className="w-3 h-3 text-cyan-400" /> AASIST+LFCC
                </span>
                <span className="text-cyan-300 font-bold">READY</span>
              </div>
            </div>
          ) : (
            <div className="flex justify-center">
              <span className="relative flex h-3 w-3" title="System Online">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
