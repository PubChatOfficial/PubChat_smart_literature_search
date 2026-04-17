import React from 'react';
import { CaretLeft } from '@phosphor-icons/react';
import { useTheme } from '@/utils/ThemeContext';
import './BackButton.css';

interface BackButtonProps {
    label?: string; // Optional custom label
    className?: string; // Optional custom class
    onClick?: () => void; // Optional custom click handler (if not just navigate(-1))
}

export const BackButton: React.FC<BackButtonProps> = ({ onClick }) => {
    const { theme } = useTheme();

    return (
        <button
            className={`back-btn`}
            onClick={onClick}
        >
            <CaretLeft weight="bold" />
            <span>{theme.language === 'zh' ? '返回' : 'Back'}</span>
        </button>
    );
};
