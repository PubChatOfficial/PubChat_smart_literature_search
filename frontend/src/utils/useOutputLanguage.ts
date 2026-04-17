import { useState, useEffect } from 'react';
import { Cookies } from './cookies';

/**
 * Available output languages with their display information
 */
export const OUTPUT_LANGUAGES = [
  { value: 'zh', flag: 'https://flagcdn.com/24x18/cn.png', name: { en: '中文', zh: '中文' } },
  { value: 'en', flag: 'https://flagcdn.com/24x18/gb.png', name: { en: 'English', zh: 'English' } },
  { value: 'es', flag: 'https://flagcdn.com/24x18/es.png', name: { en: 'Español', zh: 'Español' } },
  { value: 'fr', flag: 'https://flagcdn.com/24x18/fr.png', name: { en: 'Français', zh: 'Français' } },
  { value: 'pt', flag: 'https://flagcdn.com/24x18/pt.png', name: { en: 'Português', zh: 'Português' } },
  { value: 'it', flag: 'https://flagcdn.com/24x18/it.png', name: { en: 'Italiano', zh: 'Italiano' } },
  { value: 'de', flag: 'https://flagcdn.com/24x18/de.png', name: { en: 'Deutsch', zh: 'Deutsch' } },
  { value: 'ru', flag: 'https://flagcdn.com/24x18/ru.png', name: { en: 'Pусский', zh: 'Pусский' } },
] as const;

/**
 * Custom hook to manage output language state
 * Automatically syncs with cookies
 * 
 * @returns [outputLanguage, setOutputLanguage] - Language state and setter
 */
export const useOutputLanguage = (): [string, (language: string) => void] => {
  // Initialize from cookies, default to 'en'
  const [outputLanguage, setOutputLanguage] = useState(() => {
    const savedLanguage = Cookies.getOutputLanguage();
    return savedLanguage || 'zh';
  });

  // Automatically save to cookies when language changes
  useEffect(() => {
    Cookies.setOutputLanguage(outputLanguage);
  }, [outputLanguage]);

  return [outputLanguage, setOutputLanguage];
};
