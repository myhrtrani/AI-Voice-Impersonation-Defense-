import React, { useState } from 'react';
import {
  Languages,
  Globe,
  CheckCircle2,
  Sliders,
  Volume2,
  Activity,
  Play
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function LanguageView() {
  const {
    language,
    setLanguage,
    acousticProfile,
    setAcousticProfile,
    t
  } = useLanguage();

  const [toastMessage, setToastMessage] = useState(null);
  const [activeSampleTest, setActiveSampleTest] = useState(null);

  const languagesList = [
    {
      code: 'en',
      name: 'English (US/UK)',
      native: 'English',
      flag: '🇺🇸',
      profile: 'stress_timed',
      desc: 'Standard stress-timed rhythm with balanced high-frequency LFCC vocoder detection.'
    },
    {
      code: 'es',
      name: 'Spanish',
      native: 'Español',
      flag: '🇪🇸',
      profile: 'syllable_timed',
      desc: 'Syllable-timed cadence with calibrated vowel duration stability metrics.'
    },
    {
      code: 'fr',
      name: 'French',
      native: 'Français',
      flag: '🇫🇷',
      profile: 'syllable_timed',
      desc: 'Smooth liaison and syllable cadence with nasal resonance filter adjustments.'
    },
    {
      code: 'de',
      name: 'German',
      native: 'Deutsch',
      flag: '🇩🇪',
      profile: 'stress_timed',
      desc: 'High-energy consonantal clusters with high-band fricative tolerance.'
    },
    {
      code: 'hi',
      name: 'Hindi',
      native: 'हिन्दी',
      flag: '🇮🇳',
      profile: 'syllable_timed',
      desc: 'Retroflex and aspirated consonant spectrum acoustic compensation.'
    },
    {
      code: 'te',
      name: 'Telugu',
      native: 'తెలుగు',
      flag: '🇮🇳',
      profile: 'syllable_timed',
      desc: 'Vowel-ending phonetic cadence with adapted fundamental frequency stability.'
    },
    {
      code: 'zh',
      name: 'Chinese (Mandarin)',
      native: '中文',
      flag: '🇨🇳',
      profile: 'tonal',
      desc: 'Four-tone contour compensation preventing pitch inflection false positives.'
    },
    {
      code: 'ja',
      name: 'Japanese',
      native: '日本語',
      flag: '🇯🇵',
      profile: 'mora_timed',
      desc: 'Mora-timed pitch accent contours and low spectral variance tuning.'
    },
    {
      code: 'ar',
      name: 'Arabic',
      native: 'العربية',
      flag: '🇸🇦',
      profile: 'stress_timed',
      desc: 'Pharyngeal and emphatic consonant high-frequency resonance modeling.'
    }
  ];

  const acousticProfilesList = [
    {
      id: 'stress_timed',
      title: 'Stress-Timed Acoustic Profile',
      languages: 'English, German, Arabic, Russian',
      pitchTolerance: '1.0x (Standard)',
      lfccBias: '30% Weight',
      desc: 'Optimized for languages where syllables occur at variable intervals between stressed beats. Provides sharpest high-frequency vocoder sensitivity.'
    },
    {
      id: 'syllable_timed',
      title: 'Syllable-Timed Profile',
      languages: 'Spanish, French, Hindi, Telugu, Italian',
      pitchTolerance: '1.15x (Adapted)',
      lfccBias: '28% Weight',
      desc: 'Calibrated for languages with equal syllable durations. Adjusts cycle jitter tolerance to avoid flagging natural rhythmic syllabic transitions.'
    },
    {
      id: 'tonal',
      title: 'Tonal Inflection Profile',
      languages: 'Chinese (Mandarin), Vietnamese, Thai, Cantonese',
      pitchTolerance: '1.40x (Wide Glides)',
      lfccBias: '32% Weight',
      desc: 'Compensates for rapid linguistic tone changes (e.g. 1st-4th tone in Mandarin) so natural voice pitch inflections are not misdiagnosed as robotic anomalies.'
    },
    {
      id: 'mora_timed',
      title: 'Mora-Timed Pitch Accent Profile',
      languages: 'Japanese, Luganda',
      pitchTolerance: '1.10x (Mora-timed)',
      lfccBias: '30% Weight',
      desc: 'Tailored for moraic timing and pitch-accent patterns, ensuring natural discrete pitch drops are correctly interpreted.'
    }
  ];

  const samplePhrases = [
    { lang: 'en', title: 'English Sample', phrase: 'Please confirm your wire transfer authorization number.', profile: 'stress_timed' },
    { lang: 'es', title: 'Spanish Sample', phrase: 'Por favor, confirme su código de verificación bancaria.', profile: 'syllable_timed' },
    { lang: 'hi', title: 'Hindi Sample', phrase: 'कृपया अपना खाता सत्यापन वन-टाइम पासवर्ड साझा न करें।', profile: 'syllable_timed' },
    { lang: 'te', title: 'Telugu Sample', phrase: 'దయచేసి మీ బ్యాంకు ఖాతా వివరాలు మరియు OTP రహస్యంగా ఉంచండి.', profile: 'syllable_timed' },
    { lang: 'zh', title: 'Mandarin Sample', phrase: '请确认您的银行转账授权码，切勿向他人透露验证码。', profile: 'tonal' }
  ];

  const handleSelectLanguage = (code) => {
    setLanguage(code);
    setToastMessage(`Language changed to ${languagesList.find(l => l.code === code)?.name}!`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleSelectProfile = (profileId) => {
    setAcousticProfile(profileId);
    setToastMessage(`Acoustic Profile updated to ${profileId}!`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleTestPhrase = (sample) => {
    setActiveSampleTest(sample);
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(sample.phrase);
      utterance.lang = sample.lang;
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="p-4 lg:p-8 max-w-6xl mx-auto space-y-6 animate-fadeIn">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <Globe className="w-8 h-8 text-cyan-400" />
            {t('lang_title', 'Language & Acoustic Dialect Hub')}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {t('lang_subtitle', 'Select interface language and configure phonetic compensation profiles for regional accents and tonal languages.')}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-3 py-1.5 rounded-full bg-cyan-950 border border-cyan-500/40 text-cyan-300 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5" />
            <span>ACTIVE PROFILE: {acousticProfile.toUpperCase()}</span>
          </span>
        </div>
      </div>

      {/* Toast */}
      {toastMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 text-xs font-mono flex items-center justify-between animate-slideDown">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{toastMessage}</span>
          </div>
          <button onClick={() => setToastMessage(null)} className="text-slate-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}

      {/* Section 1: Choose Language Cards */}
      <div className="space-y-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Languages className="w-5 h-5 text-cyan-400" />
            {t('lang_select_title', 'Choose Interface Language')}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Switch UI labels, telemetry badges, and security guidance to your preferred language.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {languagesList.map((langItem) => {
            const isSelected = language === langItem.code;

            return (
              <div
                key={langItem.code}
                onClick={() => handleSelectLanguage(langItem.code)}
                className={`
                  p-4 rounded-2xl cursor-pointer transition-all duration-200 border relative overflow-hidden group
                  ${isSelected
                    ? 'bg-gradient-to-br from-cyan-950/70 to-blue-950/40 border-cyan-500/80 shadow-[0_0_20px_rgba(6,182,212,0.2)]'
                    : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-800/60'
                  }
                `}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{langItem.flag}</span>
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        {langItem.name}
                        {isSelected && <CheckCircle2 className="w-4 h-4 text-cyan-400" />}
                      </h3>
                      <span className="text-xs text-cyan-300/80 font-medium">{langItem.native}</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">
                    {langItem.code.toUpperCase()}
                  </span>
                </div>

                <p className="text-[11px] text-slate-400 mt-3 leading-relaxed">
                  {langItem.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Section 2: Acoustic Dialect Profiles */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md shadow-lg space-y-5">
        <div className="border-b border-slate-800 pb-3">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            {t('lang_acoustic_profile_title', 'Acoustic Tuning & Dialect Profiles')}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {t('lang_profile_desc', 'Adapts fundamental frequency tracking and LFCC thresholds to prevent false alarms caused by natural linguistic tones and phonetic cadence.')}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {acousticProfilesList.map((prof) => {
            const isSelected = acousticProfile === prof.id;

            return (
              <div
                key={prof.id}
                onClick={() => handleSelectProfile(prof.id)}
                className={`
                  p-4 rounded-xl border cursor-pointer transition-all duration-200 space-y-2.5 relative
                  ${isSelected
                    ? 'bg-cyan-950/40 border-cyan-500/80 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                  }
                `}
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-white flex items-center gap-2 font-mono">
                    <span className={`w-2.5 h-2.5 rounded-full ${isSelected ? 'bg-cyan-400 shadow-[0_0_6px_#22d3ee]' : 'bg-slate-600'}`} />
                    {prof.title}
                  </h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                    {prof.pitchTolerance}
                  </span>
                </div>

                <p className="text-[11px] text-slate-400 leading-relaxed">
                  {prof.desc}
                </p>

                <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-800/60">
                  <span>Languages: {prof.languages}</span>
                  <span className="text-cyan-300">{prof.lfccBias}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Section 3: Speech Synthesis Phrase Tester */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 to-slate-950 border border-cyan-500/30 backdrop-blur-md shadow-xl space-y-4">
        <div className="border-b border-slate-800 pb-3">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Volume2 className="w-5 h-5 text-cyan-400" />
            {t('lang_sample_tester_title', 'Multi-Language Speech Benchmark Preview')}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {t('lang_sample_tester_desc', 'Preview how the acoustic analyzer adapts to different linguistic stress patterns.')}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {samplePhrases.map((sample, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between space-y-3"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-200 font-mono">{sample.title}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300">
                    {sample.profile}
                  </span>
                </div>
                <p className="text-xs text-slate-400 italic">"{sample.phrase}"</p>
              </div>

              <button
                onClick={() => handleTestPhrase(sample)}
                className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Play Speech Synthesis</span>
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
