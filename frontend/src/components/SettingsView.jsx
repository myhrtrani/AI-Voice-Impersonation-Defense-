import React, { useState, useEffect } from 'react';
import {
  Sliders,
  ShieldCheck,
  Save,
  RotateCcw,
  Cpu,
  Activity,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
  RefreshCw,
  Clock
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function SettingsView() {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [testResult, setTestResult] = useState(null);

  // Settings State
  const [lowRiskMax, setLowRiskMax] = useState(40);
  const [highRiskMin, setHighRiskMin] = useState(70);
  const [ewmaAlpha, setEwmaAlpha] = useState(0.35);
  const [weightModel, setWeightModel] = useState(0.40);
  const [weightLfcc, setWeightLfcc] = useState(0.30);
  const [weightPitch, setWeightPitch] = useState(0.15);
  const [weightSpec, setWeightSpec] = useState(0.15);
  const [noiseReduction, setNoiseReduction] = useState(true);
  const [contextOffsets, setContextOffsets] = useState({
    general: 0.0,
    credential_reset: -10.0,
    otp_share: -20.0,
    fund_transfer: -25.0
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const res = await fetch('/settings');
      if (res.ok) {
        const data = await res.json();
        if (data.scoring) {
          setLowRiskMax(data.scoring.low_risk_max ?? 40);
          setHighRiskMin(data.scoring.high_risk_min ?? 70);
          setEwmaAlpha(data.scoring.ewma_alpha ?? 0.35);
          if (data.scoring.weights) {
            setWeightModel(data.scoring.weights.model ?? 0.40);
            setWeightLfcc(data.scoring.weights.lfcc ?? 0.30);
            setWeightPitch(data.scoring.weights.pitch_jitter ?? 0.15);
            setWeightSpec(data.scoring.weights.spectral ?? 0.15);
          }
          if (data.scoring.context_offsets) {
            setContextOffsets(data.scoring.context_offsets);
          }
        }
        if (data.system) {
          setNoiseReduction(data.system.enable_noise_reduction ?? true);
        }
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const payload = {
        low_risk_max: Number(lowRiskMax),
        high_risk_min: Number(highRiskMin),
        ewma_alpha: Number(ewmaAlpha),
        weight_model: Number(weightModel),
        weight_lfcc: Number(weightLfcc),
        weight_pitch_jitter: Number(weightPitch),
        weight_spectral: Number(weightSpec),
        enable_noise_reduction: Boolean(noiseReduction),
        context_offsets: contextOffsets
      };

      const res = await fetch('/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setToastMessage({ type: 'success', text: t('set_save_success', 'Settings successfully saved and applied to backend!') });
      } else {
        throw new Error('Server returned ' + res.status);
      }
    } catch (err) {
      setToastMessage({ type: 'error', text: `Failed to save settings: ${err.message}` });
    } finally {
      setSaving(false);
      setTimeout(() => setToastMessage(null), 4000);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all thresholds and weights to factory defaults?')) return;
    try {
      setSaving(true);
      const res = await fetch('/settings/reset', { method: 'POST' });
      if (res.ok) {
        setLowRiskMax(40);
        setHighRiskMin(70);
        setEwmaAlpha(0.35);
        setWeightModel(0.40);
        setWeightLfcc(0.30);
        setWeightPitch(0.15);
        setWeightSpec(0.15);
        setNoiseReduction(true);
        setContextOffsets({
          general: 0.0,
          credential_reset: -10.0,
          otp_share: -20.0,
          fund_transfer: -25.0
        });
        setToastMessage({ type: 'success', text: t('set_reset_success', 'Settings have been reset to factory defaults.') });
      }
    } catch (err) {
      setToastMessage({ type: 'error', text: `Failed to reset settings: ${err.message}` });
    } finally {
      setSaving(false);
      setTimeout(() => setToastMessage(null), 4000);
    }
  };

  const handleRunPipelineTest = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      const res = await fetch('/settings/test-pipeline', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setTestResult(data);
      } else {
        throw new Error('Test pipeline failed');
      }
    } catch (err) {
      setToastMessage({ type: 'error', text: `Self-test error: ${err.message}` });
    } finally {
      setTesting(false);
    }
  };

  const normalizeWeights = () => {
    const sum = weightModel + weightLfcc + weightPitch + weightSpec;
    if (sum > 0) {
      setWeightModel(Number((weightModel / sum).toFixed(2)));
      setWeightLfcc(Number((weightLfcc / sum).toFixed(2)));
      setWeightPitch(Number((weightPitch / sum).toFixed(2)));
      setWeightSpec(Number((weightSpec / sum).toFixed(2)));
    }
  };

  const totalWeight = Math.round((weightModel + weightLfcc + weightPitch + weightSpec) * 100);

  return (
    <div className="p-4 lg:p-8 max-w-6xl mx-auto space-y-6 animate-fadeIn">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <Sliders className="w-8 h-8 text-cyan-400" />
            {t('set_title', 'Detection Tuning & Calibration Control')}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {t('set_subtitle', 'Configure neural weights, acoustic feature blending, threshold offsets, and noise reduction.')}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            disabled={saving}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 hover:border-slate-600 transition shadow-sm"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>{t('set_btn_reset', 'Reset Defaults')}</span>
          </button>

          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 transition shadow-[0_0_15px_rgba(6,182,212,0.3)] disabled:opacity-50"
          >
            <Save className={`w-4 h-4 ${saving ? 'animate-spin' : ''}`} />
            <span>{saving ? 'Saving...' : t('set_btn_save', 'Save & Apply')}</span>
          </button>
        </div>
      </div>

      {/* Toast Notification */}
      {toastMessage && (
        <div className={`p-4 rounded-xl text-xs font-mono flex items-center justify-between animate-slideDown ${
          toastMessage.type === 'success' ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-300' : 'bg-red-950/80 border border-red-500/50 text-red-300'
        }`}>
          <div className="flex items-center gap-2">
            {toastMessage.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-red-400" />}
            <span>{toastMessage.text}</span>
          </div>
          <button onClick={() => setToastMessage(null)} className="text-slate-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}

      {/* Main Form Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section 1: Risk Thresholds */}
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md shadow-lg space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              {t('set_card_thresholds', 'Risk Threshold Matrix')}
            </h2>
            <span className="text-xs text-slate-400 font-mono">0.0 - 100.0 Scale</span>
          </div>

          {/* Threshold Visual Band Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span className="text-emerald-400">NORMAL (&lt; {lowRiskMax}%)</span>
              <span className="text-amber-400">WARNING ({lowRiskMax}% - {highRiskMin}%)</span>
              <span className="text-red-400">CRITICAL (&gt; {highRiskMin}%)</span>
            </div>
            <div className="w-full h-3 rounded-full bg-slate-800 flex overflow-hidden border border-slate-700">
              <div style={{ width: `${lowRiskMax}%` }} className="bg-emerald-500/80 h-full transition-all" />
              <div style={{ width: `${highRiskMin - lowRiskMax}%` }} className="bg-amber-500/80 h-full transition-all" />
              <div style={{ width: `${100 - highRiskMin}%` }} className="bg-red-500/80 h-full transition-all" />
            </div>
          </div>

          {/* Low Risk Slider */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-200">
                {t('set_low_max_label', 'Low Risk Threshold Max')}
              </label>
              <span className="px-2.5 py-0.5 rounded bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-mono text-xs font-bold">
                {lowRiskMax}%
              </span>
            </div>
            <input
              type="range"
              min="15"
              max="55"
              step="1"
              value={lowRiskMax}
              onChange={(e) => {
                const val = Number(e.target.value);
                if (val < highRiskMin) setLowRiskMax(val);
              }}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-400"
            />
            <p className="text-[11px] text-slate-400">
              {t('set_low_max_desc', 'Scores below this are classified as Normal Human Speech.')}
            </p>
          </div>

          {/* High Risk Slider */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-200">
                {t('set_high_min_label', 'High Risk Threshold Min')}
              </label>
              <span className="px-2.5 py-0.5 rounded bg-red-950 border border-red-500/40 text-red-300 font-mono text-xs font-bold">
                {highRiskMin}%
              </span>
            </div>
            <input
              type="range"
              min="55"
              max="90"
              step="1"
              value={highRiskMin}
              onChange={(e) => {
                const val = Number(e.target.value);
                if (val > lowRiskMax) setHighRiskMin(val);
              }}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-red-400"
            />
            <p className="text-[11px] text-slate-400">
              {t('set_high_min_desc', 'Scores above this trigger immediate Critical Impersonation Alerts.')}
            </p>
          </div>
        </div>

        {/* Section 2: Composite Feature Weights */}
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md shadow-lg space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-cyan-400" />
              {t('set_card_weights', 'Feature Blend Weights')}
            </h2>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                totalWeight === 100 ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40' : 'bg-amber-950 text-amber-300 border border-amber-500/40'
              }`}>
                SUM: {totalWeight}%
              </span>
              <button
                onClick={normalizeWeights}
                className="text-[10px] px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 font-mono transition"
                title="Normalize weights to 100%"
              >
                Auto 100%
              </button>
            </div>
          </div>

          {/* Model Weight */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold">
              <span className="text-slate-200">{t('set_weight_model', 'WavLM Synthetic Speech Model')}</span>
              <span className="font-mono text-cyan-300 font-bold">{Math.round(weightModel * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.80"
              step="0.05"
              value={weightModel}
              onChange={(e) => setWeightModel(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
          </div>

          {/* LFCC Weight */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold">
              <span className="text-slate-200">{t('set_weight_lfcc', 'LFCC Linear High-Band Cepstrals')}</span>
              <span className="font-mono text-purple-300 font-bold">{Math.round(weightLfcc * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.60"
              step="0.05"
              value={weightLfcc}
              onChange={(e) => setWeightLfcc(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-400"
            />
          </div>

          {/* Pitch / Jitter Weight */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold">
              <span className="text-slate-200">{t('set_weight_pitch', 'Pitch Variance & Cycle Jitter')}</span>
              <span className="font-mono text-amber-300 font-bold">{Math.round(weightPitch * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.40"
              step="0.05"
              value={weightPitch}
              onChange={(e) => setWeightPitch(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
            />
          </div>

          {/* Spectral Flatness Weight */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold">
              <span className="text-slate-200">{t('set_weight_spec', 'Spectral Flatness & Centroid')}</span>
              <span className="font-mono text-emerald-300 font-bold">{Math.round(weightSpec * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.40"
              step="0.05"
              value={weightSpec}
              onChange={(e) => setWeightSpec(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-400"
            />
          </div>
        </div>

        {/* Section 3: Smoothing & Noise Reduction */}
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md shadow-lg space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400" />
              {t('set_card_smoothing', 'Temporal Smoothing & Preprocessing')}
            </h2>
          </div>

          {/* EWMA Alpha Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-200">
                {t('set_ewma_alpha', 'EWMA Smoothing Factor (α)')}
              </label>
              <span className="px-2.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-300 font-mono text-xs font-bold">
                α = {ewmaAlpha}
              </span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.80"
              step="0.05"
              value={ewmaAlpha}
              onChange={(e) => setEwmaAlpha(Number(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
            <p className="text-[11px] text-slate-400">
              {t('set_ewma_desc', 'Higher α reacts faster to incoming chunks; Lower α provides smoother baseline.')}
            </p>
          </div>

          {/* Noise Stripper Toggle */}
          <div className="pt-2 flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <div>
              <span className="text-xs font-bold text-slate-200 block">
                {t('set_noise_stripper', 'Noise Reduction Stripper')}
              </span>
              <span className="text-[11px] text-slate-400 block mt-0.5">
                {t('set_noise_desc', 'Applies spectral gating to remove ambient room noise before feature extraction.')}
              </span>
            </div>
            <button
              onClick={() => setNoiseReduction(!noiseReduction)}
              className={`w-12 h-6 rounded-full transition-colors relative flex items-center px-0.5 ${
                noiseReduction ? 'bg-emerald-500' : 'bg-slate-700'
              }`}
            >
              <div
                className={`w-5 h-5 rounded-full bg-white transition-transform ${
                  noiseReduction ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Section 4: Context Sensitivity Offsets */}
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md shadow-lg space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-cyan-400" />
              {t('set_card_offsets', 'Context Sensitivity Reductions')}
            </h2>
          </div>
          <p className="text-xs text-slate-400">
            {t('set_offsets_desc', 'Lowers the trigger threshold by point delta during sensitive financial workflows.')}
          </p>

          <div className="space-y-3 pt-1">
            {[
              { key: 'fund_transfer', label: 'Fund Transfer Workflow', color: 'text-red-400' },
              { key: 'otp_share', label: 'OTP / 2FA Disclosure', color: 'text-orange-400' },
              { key: 'credential_reset', label: 'Credential Reset', color: 'text-yellow-400' },
              { key: 'general', label: 'General Conversation', color: 'text-emerald-400' }
            ].map((ctx) => (
              <div key={ctx.key} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800">
                <span className={`text-xs font-semibold ${ctx.color}`}>{ctx.label}</span>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="-40"
                    max="0"
                    step="1"
                    value={contextOffsets[ctx.key] ?? 0}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      setContextOffsets(prev => ({ ...prev, [ctx.key]: val }));
                    }}
                    className="w-16 px-2 py-1 rounded bg-slate-800 border border-slate-700 text-right text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                  />
                  <span className="text-xs font-mono text-slate-400">pts</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Section 5: Real-Time DSP Pipeline Benchmark Self-Test */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border border-cyan-500/30 backdrop-blur-md shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-cyan-400" />
              DSP Pipeline Benchmark & Health Self-Test
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Generates a synthetic 2.5s audio chunk and streams it through the full DSP feature extractor.
            </p>
          </div>

          <button
            onClick={handleRunPipelineTest}
            disabled={testing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-500/50 transition shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
            <span>{testing ? 'Benchmarking...' : t('set_btn_test_pipeline', 'Run DSP Benchmark Self-Test')}</span>
          </button>
        </div>

        {testResult && (
          <div className="p-4 rounded-xl bg-slate-950/80 border border-cyan-500/40 space-y-3 font-mono text-xs animate-slideDown">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2 text-emerald-400 font-bold">
                <CheckCircle2 className="w-4 h-4" />
                <span>{t('set_test_healthy', 'DSP Pipeline Operational')}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-300">
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
                <span>{t('set_test_latency', 'Pipeline Latency')}: <b className="text-cyan-300">{testResult.latency_ms} ms</b></span>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
              <div>
                <span className="text-slate-500 block">LFCC ARTIFACT</span>
                <span className="text-cyan-300 font-bold">{testResult.metrics?.lfcc_artifact_score}</span>
              </div>
              <div>
                <span className="text-slate-500 block">PITCH MEAN</span>
                <span className="text-white font-bold">{testResult.metrics?.pitch_mean_hz} Hz</span>
              </div>
              <div>
                <span className="text-slate-500 block">CYCLE JITTER</span>
                <span className="text-amber-300 font-bold">{testResult.metrics?.jitter}</span>
              </div>
              <div>
                <span className="text-slate-500 block">COMPOSITE RISK</span>
                <span className="text-emerald-300 font-bold">{testResult.metrics?.computed_composite_risk}%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
