import React, { createContext, useContext, useState, useEffect } from 'react';
import { TRANSLATIONS } from '../utils/translations';

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(() => {
    return localStorage.getItem('voice_sentry_lang') || 'en';
  });

  const [acousticProfile, setAcousticProfileState] = useState(() => {
    return localStorage.getItem('voice_sentry_acoustic_profile') || 'stress_timed';
  });

  // Sync preference with backend on initial mount
  useEffect(() => {
    fetch('/localization/languages')
      .then(res => res.json())
      .then(data => {
        if (data.current_language && !localStorage.getItem('voice_sentry_lang')) {
          setLanguageState(data.current_language);
        }
        if (data.current_acoustic_profile && !localStorage.getItem('voice_sentry_acoustic_profile')) {
          setAcousticProfileState(data.current_acoustic_profile);
        }
      })
      .catch(err => console.warn('Could not sync localization from backend:', err));
  }, []);

  const setLanguage = (langCode) => {
    setLanguageState(langCode);
    localStorage.setItem('voice_sentry_lang', langCode);

    // Auto-pick suitable acoustic profile if standard
    let profile = acousticProfile;
    if (langCode === 'zh') profile = 'tonal';
    else if (langCode === 'ja') profile = 'mora_timed';
    else if (['es', 'fr', 'hi', 'te'].includes(langCode)) profile = 'syllable_timed';
    else if (['en', 'de', 'ar'].includes(langCode)) profile = 'stress_timed';

    setAcousticProfileState(profile);
    localStorage.setItem('voice_sentry_acoustic_profile', profile);

    // Post to backend
    fetch('/localization/preference', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language: langCode, acoustic_profile: profile })
    }).catch(err => console.warn('Failed to save language preference on backend:', err));
  };

  const setAcousticProfile = (profileCode) => {
    setAcousticProfileState(profileCode);
    localStorage.setItem('voice_sentry_acoustic_profile', profileCode);

    fetch('/localization/preference', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language, acoustic_profile: profileCode })
    }).catch(err => console.warn('Failed to save acoustic profile on backend:', err));
  };

  const t = (key, fallback = '') => {
    const langDict = TRANSLATIONS[language] || TRANSLATIONS.en;
    if (langDict && langDict[key]) {
      return langDict[key];
    }
    // Fallback to English
    if (TRANSLATIONS.en && TRANSLATIONS.en[key]) {
      return TRANSLATIONS.en[key];
    }
    return fallback || key;
  };

  const isRTL = language === 'ar';

  return (
    <LanguageContext.Provider value={{
      language,
      setLanguage,
      acousticProfile,
      setAcousticProfile,
      t,
      isRTL
    }}>
      <div dir={isRTL ? 'rtl' : 'ltr'} className="w-full h-full flex flex-col">
        {children}
      </div>
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
