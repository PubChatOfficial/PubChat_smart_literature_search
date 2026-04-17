/**
 * Map global theme color to auth theme class name
 */
export function getAuthThemeClass(primaryColor: string): string {
  const colorToThemeMap: Record<string, string> = {
    '#dc2626': 'theme-red',
    '#f97316': 'theme-orange',
    '#eab308': 'theme-yellow',
    '#10b981': 'theme-green',
    '#14b8a6': 'theme-teal',
    '#3b82f6': 'theme-blue',
    '#0071bc': 'theme-blue',
    '#2f5385': 'theme-navy',
    '#6366f1': 'theme-indigo',
    '#8b5cf6': 'theme-purple',
  };

  return colorToThemeMap[primaryColor] || 'theme-teal';
}

