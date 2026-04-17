import React from 'react';
import ReactDOM from 'react-dom';
import { motion } from 'framer-motion';
import { Warning } from '@phosphor-icons/react';
import { useTheme } from '@/utils/ThemeContext';
import './ConfirmWindow.css';

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  confirmButtonColor?: 'red' | 'primary';
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText,
  cancelText,
  confirmButtonColor = 'red',
}) => {
  const { theme } = useTheme();

  const defaultTitle = theme.language === 'en' ? 'Confirm Action' : '确认操作';
  const defaultMessage = theme.language === 'en'
    ? 'Are you sure you want to proceed? This action cannot be undone.'
    : '您确定要继续吗？此操作不可逆。';
  const defaultConfirmText = theme.language === 'en' ? 'Confirm' : '确认';
  const defaultCancelText = theme.language === 'en' ? 'Cancel' : '取消';

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return ReactDOM.createPortal(
    <div className="confirm-modal-backdrop" onClick={handleBackdropClick}>
      <motion.div
        className="confirm-modal"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.2 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="confirm-modal-header">
          <div className="confirm-modal-icon">
            <Warning size={32} weight="fill" />
          </div>
          <h3 className="confirm-modal-title">
            {title || defaultTitle}
          </h3>
        </div>
        <div className="confirm-modal-content">
          <p className="confirm-modal-message">
            {message || defaultMessage}
          </p>
        </div>
        <div className="confirm-modal-actions">
          <button
            className="confirm-modal-cancel"
            onClick={onClose}
          >
            {cancelText || defaultCancelText}
          </button>
          <button
            className={`confirm-modal-ok ${confirmButtonColor === 'red' ? 'red' : 'primary'}`}
            onClick={onConfirm}
          >
            {confirmText || defaultConfirmText}
          </button>
        </div>
      </motion.div>
    </div>,
    document.body
  );
};

