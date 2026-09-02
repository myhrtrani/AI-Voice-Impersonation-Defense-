import React from 'react';
import { Cpu, Activity, Info } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function Navbar({ transactionContext, noiseReductionActive, onOpenScalePanel, activePage }) {
  const { t } = useLanguage();

  const getContextBadge = (ctx) => {
    switch (ctx) {
      case 'fund_transfer':
        return { label: t('badge_fund_transfer', 'FUND TRANSFER (MAX SENSITIVITY)'), color: 'bg-red-500/20 text-red-400 border-red-500/40' };
      case 'otp_share':
        return { label: t('badge_otp_share', 'OTP / 2FA DISCLOSURE (HIGH)'), color: 'bg-orange-500/20 text-orange-400 border-orange-500/40' };
      case 'credential_reset':
        return { label: t('badge_credential_reset', 'CREDENTIAL RESET'), color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40' };
      default:
        return { label: t('badge_general', 'GENERAL CONVERSATION'), color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' };
    }
  };

  const badge = getContextBadge(transactionContext);

  return (
    <header className="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur-md sticky top-0 z-30 px-4 lg:px-8 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Left: Section Breadcrumb */}
        <div className="flex items-center gap-3 pl-10 lg:pl-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
              {activePage === 'live_sentry' ? 'AI Sentry Detection' : activePage.toUpperCase().replace('_', ' ')}
            </span>
            <span className="text-slate-600">/</span>
            <span className="text-xs font-mono text-cyan-400 font-semibold">
              {t('nav_status_ready', 'SYSTEM READY')}
            </span>
          </div>
        </div>

        {/* Center: Live Telemetry Badges */}
        <div className="flex items-center gap-2 flex-wrap justify-center">
          {/* Active Context */}
          <div className={`px-2.5 py-1 rounded-full text-xs font-mono font-semibold border ${badge.color} flex items-center gap-1.5`}>
            <Activity className="w-3.5 h-3.5" />
            <span>{badge.label}</span>
          </div>

          {/* Noise Stripper Status */}
          <div className="px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span>{t('badge_noise_stripper', 'NOISE STRIPPER')}: {noiseReductionActive ? 'ACTIVE' : 'BYPASS'}</span>
          </div>

          {/* LFCC High-Band Engine */}
          <div className="hidden sm:flex px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5" />
            <span>{t('badge_lfcc_scanner', 'WAVLM + LFCC SCANNER')}</span>
          </div>
        </div>

        {/* Right: Quick Language Pill & Architecture Modal */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onOpenScalePanel}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-slate-600 transition shadow-sm"
          >
            <Info className="w-3.5 h-3.5 text-cyan-400" />
            <span>{t('badge_scale_info', 'Architecture Specs')}</span>
          </button>
        </div>
      </div>
    </header>
  );
}

