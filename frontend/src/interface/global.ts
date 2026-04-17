
// Theme related types
export type ThemeMode = 'light' | 'dark';

export type Language = 'en' | 'zh';

export interface ThemeColor {
    color: string;
    hover: string;
    name: {
        en: string;
        zh: string;
    };
}

export const THEME_COLORS: ThemeColor[] = [
    { color: '#dc2626', hover: '#b91c1c', name: { en: 'Red', zh: '红色' } },
    { color: '#f97316', hover: '#ea580c', name: { en: 'Orange', zh: '橙色' } },
    { color: '#eab308', hover: '#ca8a04', name: { en: 'Yellow', zh: '黄色' } },
    { color: '#10b981', hover: '#059669', name: { en: 'Green', zh: '绿色' } },
    { color: '#14b8a6', hover: '#0d9488', name: { en: 'Teal', zh: '青色' } },
    { color: '#0071bc', hover: '#0062a3', name: { en: 'Blue', zh: '蓝色' } },
    { color: '#20558A', hover: '#0271BD', name: { en: 'Slate', zh: '石墨灰' } },
    { color: '#6366f1', hover: '#4f46e5', name: { en: 'Indigo', zh: '靛蓝' } },
    { color: '#8b5cf6', hover: '#7c3aed', name: { en: 'Purple', zh: '紫色' } },

];

export interface ThemeState {
    mode: ThemeMode;
    language: Language;
    primaryColor: string;
    primaryHover: string;
}


// ApiResponse
export interface ApiResponse<T = null> {
    success: boolean;
    message: {
        zh: string;
        en: string;
    };
    data?: T;
}