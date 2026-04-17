/**
 * Task Status Utility
 * 任务状态管理工具
 * 
 * 提供任务状态的类型定义、文本获取函数等通用功能
 */

export type TaskStatus = 'Initializing' | 'Waiting' | 'Running' | 'Success' | 'Failed';

/**
 * 获取状态文本（支持多语言）
 * @param status 任务状态
 * @param language 语言代码 ('en' | 'zh')
 * @returns 状态文本
 */
export const getStatusText = (status: TaskStatus, language: string = 'en'): string => {
  const statusTexts: Record<TaskStatus, { en: string; zh: string }> = {
    Initializing: { en: 'Initializing', zh: '初始化中' },
    Waiting: { en: 'Waiting', zh: '等待中' },
    Running: { en: 'Running', zh: '运行中' },
    Success: { en: 'Success', zh: '成功' },
    Failed: { en: 'Failed', zh: '失败' },
  };

  const lang = language === 'zh' ? 'zh' : 'en';
  return statusTexts[status]?.[lang] || statusTexts.Waiting[lang];
};

/**
 * 获取状态颜色（用于状态指示器）
 * @param status 任务状态
 * @returns 颜色代码
 */
export const getStatusColor = (status: TaskStatus): string => {
  const colors: Record<TaskStatus, string> = {
    Initializing: '#3B82F6', // Blue
    Waiting: '#9CA3AF',      // Gray
    Running: '#F59E0B',      // Orange/Amber
    Success: '#10B981',      // Green
    Failed: '#EF4444',      // Red
  };
  return colors[status] || colors.Waiting;
};

/**
 * 获取状态徽章样式配置
 * @param status 任务状态
 * @returns 包含背景色和文字色的配置对象
 */
export const getStatusBadgeStyle = (status: TaskStatus): { backgroundColor: string; color: string } => {
  const styles: Record<TaskStatus, { backgroundColor: string; color: string }> = {
    Initializing: { backgroundColor: '#DBEAFE', color: '#1E40AF' },
    Waiting: { backgroundColor: '#E5E7EB', color: '#4B5563' },
    Running: { backgroundColor: '#FEF3C7', color: '#B45309' },
    Success: { backgroundColor: '#D1FAE5', color: '#047857' },
    Failed: { backgroundColor: '#FEE2E2', color: '#DC2626' },
  };
  return styles[status] || styles.Waiting;
};

/**
 * 获取深色模式下的状态徽章样式配置
 * @param status 任务状态
 * @returns 包含背景色和文字色的配置对象
 */
export const getStatusBadgeStyleDark = (status: TaskStatus): { backgroundColor: string; color: string } => {
  const styles: Record<TaskStatus, { backgroundColor: string; color: string }> = {
    Initializing: { backgroundColor: 'rgba(219, 234, 254, 0.3)', color: '#93C5FD' },
    Waiting: { backgroundColor: 'rgba(229, 231, 235, 0.3)', color: '#9CA3AF' },
    Running: { backgroundColor: 'rgba(254, 243, 199, 0.3)', color: '#FCD34D' },
    Success: { backgroundColor: 'rgba(209, 250, 229, 0.3)', color: '#6EE7B7' },
    Failed: { backgroundColor: 'rgba(254, 226, 226, 0.3)', color: '#FCA5A5' },
  };
  return styles[status] || styles.Waiting;
};

/**
 * 检查状态是否需要动画
 * @param status 任务状态
 * @returns 是否需要动画
 */
export const shouldAnimateStatus = (status: TaskStatus): boolean => {
  return status === 'Initializing' || status === 'Running';
};

