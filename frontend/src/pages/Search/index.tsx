import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '@/utils/ThemeContext';
import { useToast } from '@/components/Toast/ToastContext';
import { Cookies } from '@/utils/cookies';
import { ArrowUpIcon } from '@phosphor-icons/react';
import { motion } from 'framer-motion';
import './Search.css';

const translations = {
  en: {
    welcomeTitle: 'Welcome to PubChat!',
    welcomeSubtitle: 'Start your intelligent Literature Search journey right now.',
    searchPlaceholder: 'Enter your search here...',
  },
  zh: {
    welcomeTitle: '欢迎来到PubChat!',
    welcomeSubtitle: '现在就开始你的智能文献检索之旅吧。',
    searchPlaceholder: '请输入您的检索问题...',
  },
};

export const LiteratureSearch: React.FC = () => {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const toast = useToast();
  const [subtitleText, setSubtitleText] = useState('');
  const [showCursor, setShowCursor] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Check for existing search task
  useEffect(() => {
    // Check if we have a task ID in cookies
    const existingTaskId = Cookies.getSearchTaskId();
    if (existingTaskId?.display) {
      // If task ID exists, redirect to results
      navigate('/search/result');
    }
  }, [navigate]);

  const t = translations[theme.language];

  const renderSubtitle = () => {
    const text = subtitleText;
    if (theme.language === 'en') {
      // For English: highlight "Literature Search"
      const parts = text.split(/(Literature Search)/i);
      return parts.map((part, index) =>
        part.toLowerCase() === 'literature search' ? (
          <span key={index} className="highlight-text">{part}</span>
        ) : (
          part
        )
      );
    } else {
      // For Chinese: highlight "文献检索"
      const parts = text.split(/(文献检索)/);
      return parts.map((part, index) =>
        part === '文献检索' ? (
          <span key={index} className="highlight-text">{part}</span>
        ) : (
          part
        )
      );
    }
  };

  useEffect(() => {
    let subtitleIndex = 0;
    const textLength = t.welcomeSubtitle.length;

    // 固定总打字时间为2秒，无论中英文
    const totalDuration = 1800;
    // 根据字符数量计算每个字符的间隔时间
    const typingSpeed = totalDuration / textLength;

    let animationId: number;
    let lastTime = 0;

    const typeSubtitle = (currentTime: number) => {
      if (lastTime === 0) lastTime = currentTime;

      const elapsed = currentTime - lastTime;

      if (elapsed >= typingSpeed) {
        if (subtitleIndex < textLength) {
          setSubtitleText(t.welcomeSubtitle.substring(0, subtitleIndex + 1));
          subtitleIndex++;
          lastTime = currentTime;
        } else {
          // 打字完成后隐藏光标
          setShowCursor(false);
          return;
        }
      }

      animationId = requestAnimationFrame(typeSubtitle);
    };

    // Reset and start typing subtitle
    setSubtitleText('');
    setShowCursor(true);
    const startTimeout = setTimeout(() => {
      animationId = requestAnimationFrame(typeSubtitle);
    }, 300);

    return () => {
      clearTimeout(startTimeout);
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, [theme.language, t.welcomeSubtitle]);

  const handleSearch = () => {
    // 如果输入框为空，显示提示信息
    toast.showWarning(
      theme.language === 'en'
        ? 'Please enter your search query'
        : '请输入您的检索问题'
    );
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleInputClick = () => {
    // 当用户点击输入框时，立即跳转到 LiteratureTask 页面
    navigate('/search/task', { state: { query: searchQuery } });
  };

  return (
    <div className="welcome-content">
      <div className="welcome-box">
        <h1 className="welcome-title">
          {t.welcomeTitle}
        </h1>
        <p className="welcome-subtitle">
          {renderSubtitle()}
          {showCursor && <span className="cursor">|</span>}
        </p>

        <div className="search-container">
          <motion.div
            layoutId="search-input-container"
            layout={false}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 30,
            }}
            style={{ position: 'relative', width: '100%' }}
          >
            <input
              type="text"
              className="literatureSearch-search-input"
              placeholder={t.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleKeyPress}
              onClick={handleInputClick}
            />
            <button className="arrow-up-button" onClick={handleSearch}>
              <ArrowUpIcon weight="bold" size={20} />
            </button>
          </motion.div>
          {/* <button className="start-search-btn" onClick={handleSearch}>
            {t.startSearch}
          </button> */}
        </div>
      </div>

      {/* <footer className="literatureSearch-footer">
        <span>Copyright © 2026 PubChat. All rights reserved.</span>
      </footer> */}
    </div>
  );
};

