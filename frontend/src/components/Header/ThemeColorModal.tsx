import React from 'react';
import ReactDOM from 'react-dom';
import { X } from '@phosphor-icons/react';
import { useTheme } from '@/utils/ThemeContext';
import { THEME_COLORS, ThemeColor } from '@/interface/global';
import './ThemeColorModal.css';

interface ThemeColorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ThemeColorModal: React.FC<ThemeColorModalProps> = ({ isOpen, onClose }) => {
  const { theme, setPrimaryColor } = useTheme();

  if (!isOpen) return null;

  const handleColorSelect = (colorConfig: ThemeColor) => {
    setPrimaryColor(colorConfig.color, colorConfig.hover);
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // 获取当前选中的颜色信息
  const selectedColor = THEME_COLORS.find(c => c.color === theme.primaryColor);

  const texts = {
    title: { en: 'Theme Colors', zh: '主题颜色' },
    subtitle: { en: 'Choose your preferred theme color', zh: '选择您喜欢的主题颜色' },
    description: {
      '#dc2626': { en: 'Bold and energetic', zh: '热情奔放' },
      '#f97316': { en: 'Warm and vibrant', zh: '温暖活力' },
      '#eab308': { en: 'Bright and optimistic', zh: '明亮乐观' },
      '#10b981': { en: 'Fresh and natural', zh: '清新自然' },
      '#14b8a6': { en: 'Calm and refreshing', zh: '平静清爽' },
      '#3b82f6': { en: 'Professional and trustworthy', zh: '专业可靠' },
      '#2f5385': { en: 'Elegant and sophisticated', zh: '优雅稳重' },
      '#6366f1': { en: 'Creative and modern', zh: '创意现代' },
      '#8b5cf6': { en: 'Unique and imaginative', zh: '独特浪漫' },
    } as Record<string, { en: string; zh: string }>
  };

  const modalContent = (
    <div className="theme-modal-backdrop" onClick={handleBackdropClick}>
      <div className="theme-modal">
        {/* Header */}
        <div className="theme-modal-header">
          <div className="theme-modal-title-wrapper">
            <div className="theme-modal-icon" style={{ background: `linear-gradient(135deg, ${theme.primaryColor}, ${theme.primaryHover})` }} />
            <h2 className="theme-modal-title">{texts.title[theme.language]}</h2>
          </div>
          <button className="theme-modal-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="theme-modal-content">
          <p className="theme-modal-subtitle">{texts.subtitle[theme.language]}</p>

          <div className="theme-color-grid">
            {THEME_COLORS.map((colorConfig) => (
              <button
                key={colorConfig.color}
                className={`theme-color-btn ${theme.primaryColor === colorConfig.color ? 'active' : ''}`}
                style={{ backgroundColor: colorConfig.color }}
                onClick={() => handleColorSelect(colorConfig)}
              >
                {colorConfig.name[theme.language]}
                {theme.primaryColor === colorConfig.color && (
                  <span className="theme-color-check">●</span>
                )}
              </button>
            ))}
          </div>

          {/* Selected color info */}
          {selectedColor && (
            <div className="theme-color-info">
              <div className="theme-color-info-dot" style={{ backgroundColor: selectedColor.color }} />
              <div className="theme-color-info-text">
                <span className="theme-color-info-name">{selectedColor.name[theme.language]}</span>
                <span className="theme-color-info-desc">
                  {texts.description[selectedColor.color]?.[theme.language] || ''}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // 使用 Portal 将 Modal 渲染到 body，避免被父元素的 z-index 限制
  return ReactDOM.createPortal(modalContent, document.body);
};

