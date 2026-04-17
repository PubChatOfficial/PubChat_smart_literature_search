import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ThemeMode, Language, ThemeState, THEME_COLORS } from '@/interface/global';
import { Cookies } from '@/utils/cookies';

interface ThemeContextType {
  theme: ThemeState;
  setMode: (mode: ThemeMode) => void;
  setLanguage: (language: Language) => void;
  setPrimaryColor: (color: string, hover: string) => void;
  toggleMode: () => void;
  toggleLanguage: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const defaultColor = THEME_COLORS.find(c => c.color === '#20558A') || THEME_COLORS[5];

// Logo filter映射 - 将红色SVG转换为各主题色
// 这些filter值是通过CSS filter generator计算得出的
const LOGO_FILTERS: Record<string, string> = {
  '#dc2626': 'brightness(0) saturate(100%) invert(18%) sepia(89%) saturate(5765%) hue-rotate(356deg) brightness(96%) contrast(87%)', // Red
  '#f97316': 'brightness(0) saturate(100%) invert(54%) sepia(74%) saturate(2274%) hue-rotate(360deg) brightness(99%) contrast(96%)', // Orange
  '#eab308': 'brightness(0) saturate(100%) invert(73%) sepia(68%) saturate(621%) hue-rotate(11deg) brightness(96%) contrast(91%)', // Yellow
  '#10b981': 'brightness(0) saturate(100%) invert(58%) sepia(47%) saturate(573%) hue-rotate(109deg) brightness(94%) contrast(89%)', // Green
  '#14b8a6': 'brightness(0) saturate(100%) invert(60%) sepia(45%) saturate(547%) hue-rotate(127deg) brightness(92%) contrast(90%)', // Teal
  '#0071bc': 'brightness(0) saturate(100%) invert(32%) sepia(98%) saturate(1910%) hue-rotate(193deg) brightness(93%) contrast(101%)', // Blue (PubMed)
  '#6366f1': 'brightness(0) saturate(100%) invert(42%) sepia(79%) saturate(2476%) hue-rotate(227deg) brightness(99%) contrast(91%)', // Indigo
  '#8b5cf6': 'brightness(0) saturate(100%) invert(42%) sepia(93%) saturate(1352%) hue-rotate(228deg) brightness(97%) contrast(93%)', // Purple
  '#20558A': 'brightness(0) saturate(100%) invert(47%) sepia(14%) saturate(484%) hue-rotate(176deg) brightness(93%) contrast(87%)', // Slate
};

// 检测浏览器默认语言
const detectBrowserLanguage = (): Language => {
  // if (typeof window === 'undefined') return 'en';
  // const browserLang = navigator.language || (navigator as any).userLanguage;
  // return browserLang.toLowerCase().includes('zh') ? 'zh' : 'en';

  // 修改这里：直接返回 'en' (英文) 或 'zh' (中文) 作为默认语言
  return 'en';
};

// 检测浏览器深色模式偏好
const detectBrowserThemeMode = (): ThemeMode => {
  // if (typeof window === 'undefined') return 'light';

  // // 检查浏览器是否支持深色模式查询
  // if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
  //   return 'dark';
  // }
  return 'light';
};

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<ThemeState>(() => {
    // 优先使用保存的模式，如果没有则检测浏览器偏好
    const savedMode = Cookies.getThemeMode();
    const defaultMode = savedMode ?? detectBrowserThemeMode();

    // 优先使用保存的语言，如果没有则检测浏览器语言
    const savedLanguage = Cookies.getLanguage();
    const defaultLanguage = savedLanguage ?? detectBrowserLanguage();

    const savedColor = Cookies.getPrimaryColor() ?? defaultColor.color;
    // Force migration from old default Slate to new default Blue if user hasn't explicitly changed it (or even if they did, if we consider Slate 'deprecated' as default)
    const effectiveColor = (savedColor === '#2f5385') ? '#2f5385' : savedColor;

    const colorConfig = THEME_COLORS.find(c => c.color === effectiveColor) || defaultColor;

    return {
      mode: defaultMode as ThemeMode,
      language: defaultLanguage as Language,
      primaryColor: colorConfig.color,
      primaryHover: colorConfig.hover,
    };
  });

  useEffect(() => {
    // 强制同步 hover 颜色，防止 cookie 中保存了错误的旧值
    const config = THEME_COLORS.find(c => c.color === theme.primaryColor);
    if (config && config.hover !== theme.primaryHover) {
      setTheme(prev => ({ ...prev, primaryHover: config.hover }));
      // Don't need to save cookie here, it will be saved on next change or handled by setPrimaryColor
    }

    // Apply theme to document
    const root = document.documentElement;
    root.style.setProperty('--primary-color', theme.primaryColor);
    root.style.setProperty('--primary-hover', theme.primaryHover);

    const hex = theme.primaryColor.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    root.style.setProperty('--primary-rgba', `${r}, ${g}, ${b}`);

    // 设置logo filter以匹配主题色
    const logoFilter = LOGO_FILTERS[theme.primaryColor] || LOGO_FILTERS['#10b981'];
    root.style.setProperty('--logo-filter', logoFilter);

    if (theme.mode === 'dark') {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, [theme]);

  const setMode = (mode: ThemeMode) => {
    setTheme(prev => ({ ...prev, mode }));
    Cookies.setThemeMode(mode);
  };

  const setLanguage = (language: Language) => {
    setTheme(prev => ({ ...prev, language }));
    Cookies.setLanguage(language);
  };

  const setPrimaryColor = (color: string, hover: string) => {
    setTheme(prev => ({ ...prev, primaryColor: color, primaryHover: hover }));
    Cookies.setPrimaryColor(color);
  };

  const toggleMode = () => {
    setMode(theme.mode === 'light' ? 'dark' : 'light');
  };

  const toggleLanguage = () => {
    setLanguage(theme.language === 'en' ? 'zh' : 'en');
  };

  return (
    <ThemeContext.Provider value={{ theme, setMode, setLanguage, setPrimaryColor, toggleMode, toggleLanguage }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

