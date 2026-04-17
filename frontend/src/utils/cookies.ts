// Cookies utilities for storing user session and task data

export interface CookieOptions {
  expires?: number; // Days until expiration (default: 30 days)
  path?: string; // Cookie path (default: '/')
  domain?: string; // Cookie domain
  secure?: boolean; // HTTPS only (default: false)
  sameSite?: 'strict' | 'lax' | 'none'; // SameSite attribute (default: 'lax')
}

export const COOKIE_KEYS = {
  SESSION_ID: 'pubchat_sessionid',
  OUTPUT_LANGUAGE: 'pubchat_output_language',
  THEME_MODE: 'pubchat_theme_mode',
  THEME_MODE_MANUAL: 'pubchat_theme_mode_manual',
  LANGUAGE: 'pubchat_language',
  PRIMARY_COLOR: 'pubchat_primary_color',
  SIDEBAR_COLLAPSED: 'pubchat_sidebar_collapsed',
  PUBMED_LIMITS: 'pubchat_pubmed_limits',
  JOURNAL_LIMITS: 'pubchat_journal_limits',
  SEARCH_SETTINGS: 'pubchat_search_settings',
  SEARCH_TASK_ID: 'pubchat_search_task_id',
  AI_API_MODEL: 'pubchat_ai_api_model',
} as const;

/**
 * Get a cookie value by key
 * @param key - Cookie key
 * @returns Cookie value or null if not found
 */
export const getCookie = (key: string): string | null => {
  if (typeof document === 'undefined') {
    return null;
  }

  const name = key + '=';
  const cookieArray = document.cookie.split(';');

  for (let i = 0; i < cookieArray.length; i++) {
    let cookie = cookieArray[i];
    while (cookie.charAt(0) === ' ') {
      cookie = cookie.substring(1);
    }
    if (cookie.indexOf(name) === 0) {
      return decodeURIComponent(cookie.substring(name.length, cookie.length));
    }
  }

  return null;
};

/**
 * Set a cookie value
 * @param key - Cookie key
 * @param value - Cookie value
 * @param options - Cookie options (expires, path, domain, secure, sameSite)
 */
export const setCookie = (
  key: string,
  value: string,
  options: CookieOptions = {}
): void => {
  if (typeof document === 'undefined') {
    return;
  }

  const {
    expires = 30, // Default: 30 days
    path = '/',
    domain,
    secure = false,
    sameSite = 'lax',
  } = options;

  let cookieString = `${key}=${encodeURIComponent(value)}`;

  // Add expiration
  if (expires) {
    const date = new Date();
    date.setTime(date.getTime() + expires * 24 * 60 * 60 * 1000);
    cookieString += `; expires=${date.toUTCString()}`;
  }

  // Add path
  cookieString += `; path=${path}`;

  // Add domain if specified
  if (domain) {
    cookieString += `; domain=${domain}`;
  }

  // Add secure flag
  if (secure) {
    cookieString += '; secure';
  }

  // Add SameSite attribute
  cookieString += `; SameSite=${sameSite}`;

  document.cookie = cookieString;
};

/**
 * Remove a cookie
 * @param key - Cookie key
 * @param options - Cookie options (path, domain)
 */
export const removeCookie = (
  key: string,
  options: { path?: string; domain?: string } = {}
): void => {
  if (typeof document === 'undefined') {
    return;
  }

  const { path = '/', domain } = options;

  let cookieString = `${key}=; expires=Thu, 01 Jan 1970 00:00:00 UTC`;

  // Add path
  cookieString += `; path=${path}`;

  // Add domain if specified
  if (domain) {
    cookieString += `; domain=${domain}`;
  }

  document.cookie = cookieString;
};

/**
 * Get a cookie value and parse it as JSON
 * @param key - Cookie key
 * @param defaultValue - Default value if cookie doesn't exist
 * @returns Parsed value or default value
 */
export const getCookieAsJson = <T>(key: string, defaultValue?: T): T | null => {
  try {
    const value = getCookie(key);
    if (value === null) {
      return defaultValue ?? null;
    }
    return JSON.parse(value) as T;
  } catch {
    return defaultValue ?? null;
  }
};

/**
 * Set a cookie value with JSON serialization
 * @param key - Cookie key
 * @param value - Value to store (will be JSON stringified)
 * @param options - Cookie options
 */
export const setCookieAsJson = <T>(
  key: string,
  value: T,
  options: CookieOptions = {}
): void => {
  try {
    const jsonValue = JSON.stringify(value);
    setCookie(key, jsonValue, options);
  } catch (error) {
    console.error('Error saving to cookie:', error);
  }
};

/**
 * Cookies utility object with all methods
 */
export const Cookies = {
  /**
   * Get a cookie value as JSON
   */
  get: getCookieAsJson,

  /**
   * Set a cookie value with JSON serialization
   */
  set: setCookieAsJson,

  /**
   * Remove a cookie
   */
  remove: removeCookie,

  /**
   * Get raw cookie value (string, not JSON parsed)
   */
  getRaw: getCookie,

  /**
   * Set raw cookie value (string, not JSON stringified)
   */
  setRaw: setCookie,

  /**
   * Get session ID (same as token)
   */
  getSessionId: (): string | null => {
    return getCookie(COOKIE_KEYS.SESSION_ID);
  },

  /**
   * Set session ID (same as token)
   */
  setSessionId: (sessionId: string, options?: CookieOptions): void => {
    setCookie(COOKIE_KEYS.SESSION_ID, sessionId, options);
  },

  /**
   * Get token (same as session ID)
   */
  getToken: (): string | null => {
    return getCookie(COOKIE_KEYS.SESSION_ID);
  },

  /**
   * Set token (same as session ID)
   */
  setToken: (token: string, options?: CookieOptions): void => {
    setCookie(COOKIE_KEYS.SESSION_ID, token, options);
  },

  /**
   * Get search task ID
   */
  getSearchTaskId: (): { taskId: string; display: boolean } | null => {
    return getCookieAsJson<{ taskId: string; display: boolean }>(COOKIE_KEYS.SEARCH_TASK_ID);
  },

  /**
   * Set search task ID
   */
  setSearchTaskId: (data: { taskId: string; display: boolean }, options?: CookieOptions): void => {
    setCookieAsJson(COOKIE_KEYS.SEARCH_TASK_ID, data, options);
  },

  /**
   * Remove search task ID
   */
  removeSearchTaskId: (options?: { path?: string; domain?: string }): void => {
    removeCookie(COOKIE_KEYS.SEARCH_TASK_ID, options);
  },

  /**
   * Get output language
   */
  getOutputLanguage: (): string | null => {
    return getCookie(COOKIE_KEYS.OUTPUT_LANGUAGE);
  },

  /**
   * Set output language
   */
  setOutputLanguage: (language: string, options?: CookieOptions): void => {
    setCookie(COOKIE_KEYS.OUTPUT_LANGUAGE, language, options);
  },

  /**
   * Get theme mode
   */
  getThemeMode: (): string | null => {
    return getCookieAsJson<string>(COOKIE_KEYS.THEME_MODE);
  },

  /**
   * Set theme mode
   */
  setThemeMode: (mode: string, options?: CookieOptions): void => {
    setCookieAsJson(COOKIE_KEYS.THEME_MODE, mode, options);
  },

  /**
   * Get theme mode manual flag
   */
  getThemeModeManual: (): boolean | null => {
    return getCookieAsJson<boolean>(COOKIE_KEYS.THEME_MODE_MANUAL);
  },

  /**
   * Set theme mode manual flag
   */
  setThemeModeManual: (manual: boolean, options?: CookieOptions): void => {
    setCookieAsJson(COOKIE_KEYS.THEME_MODE_MANUAL, manual, options);
  },

  /**
   * Get language
   */
  getLanguage: (): string | null => {
    return getCookieAsJson<string>(COOKIE_KEYS.LANGUAGE);
  },

  /**
   * Set language
   */
  setLanguage: (language: string, options?: CookieOptions): void => {
    setCookieAsJson(COOKIE_KEYS.LANGUAGE, language, options);
  },

  /**
   * Get primary color
   */
  getPrimaryColor: (): string | null => {
    return getCookieAsJson<string>(COOKIE_KEYS.PRIMARY_COLOR);
  },

  /**
   * Set primary color
   */
  setPrimaryColor: (color: string, options?: CookieOptions): void => {
    setCookieAsJson(COOKIE_KEYS.PRIMARY_COLOR, color, options);
  },

  /**
   * Get sidebar collapsed state
   */
  getSidebarCollapsed: (): boolean | null => {
    return getCookieAsJson<boolean>(COOKIE_KEYS.SIDEBAR_COLLAPSED);
  },

  /**
   * Set sidebar collapsed state
   */
  setSidebarCollapsed: (collapsed: boolean, options?: CookieOptions): void => {
    setCookieAsJson(COOKIE_KEYS.SIDEBAR_COLLAPSED, collapsed, options);
  },

  /**
   * Get PubMed limits
   */
  getPubMedLimits: <T>(): T | null => {
    return getCookieAsJson<T>(COOKIE_KEYS.PUBMED_LIMITS);
  },

  /**
   * Set PubMed limits
   */
  setPubMedLimits: <T>(limits: T, options?: CookieOptions): void => {
    setCookieAsJson(COOKIE_KEYS.PUBMED_LIMITS, limits, options);
  },

  /**
   * Get Journal limits
   */
  getJournalLimits: <T>(): T | null => {
    return getCookieAsJson<T>(COOKIE_KEYS.JOURNAL_LIMITS);
  },

  /**
   * Set Journal limits
   */
  setJournalLimits: <T>(limits: T, options?: CookieOptions): void => {
    setCookieAsJson(COOKIE_KEYS.JOURNAL_LIMITS, limits, options);
  },

  /**
   * Get Search settings
   */
  getSearchSettings: <T>(): T | null => {
    return getCookieAsJson<T>(COOKIE_KEYS.SEARCH_SETTINGS);
  },

  /**
   * Set Search settings
   */
  setSearchSettings: <T>(settings: T, options?: CookieOptions): void => {
    setCookieAsJson(COOKIE_KEYS.SEARCH_SETTINGS, settings, options);
  },

  /**
   * AI 接口配置（模型 + API Key）
   */
  getAiApiModel: (): { preset: string; customModel: string; apiKey: string } | null => {
    return getCookieAsJson<{ preset: string; customModel: string; apiKey: string }>(COOKIE_KEYS.AI_API_MODEL);
  },

  setAiApiModel: (
    data: { preset: string; customModel: string; apiKey: string },
    options?: CookieOptions
  ): void => {
    setCookieAsJson(COOKIE_KEYS.AI_API_MODEL, data, options);
  },

};


