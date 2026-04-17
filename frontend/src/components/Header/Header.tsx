import React, { useState, useEffect } from 'react';
import { Sun, Moon, Palette, Translate, CaretDown, CaretUp } from '@phosphor-icons/react';
import { useTheme } from '@/utils/ThemeContext';
import { MobileMenuButton, useMobileMenu } from '../SideBar/SideBar';
import { ThemeColorModal } from './ThemeColorModal';
import { NihIcon } from '@/icons/nih';
import '@/styles/global.css';

export const Header: React.FC = () => {
  const { theme, toggleMode, toggleLanguage } = useTheme();
  const [colorModalOpen, setColorModalOpen] = useState(false);
  const mobileMenuContext = useMobileMenu();

  // 初始化时直接检查窗口大小，避免移动端刷新时的布局闪烁
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth <= 900;
    }
    return false;
  });

  const [isExpanded, setIsExpanded] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth > 900; // 桌面端默认展开
    }
    return false; // 默认收起
  });

  // 检测移动端
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth <= 900;
      const wasMobile = isMobile;
      setIsMobile(mobile);

      // 只在从桌面切换到移动端时自动收起
      // 不在从移动端切换到桌面端时自动展开
      if (wasMobile === false && mobile === true) {
        // 从桌面变移动端时，收起
        setIsExpanded(false);
      }
    };

    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [isMobile]); // 添加 isMobile 依赖

  // 互斥逻辑：Sidebar 打开时，关闭 Header 菜单
  useEffect(() => {
    if (mobileMenuContext?.isMobileMenuOpen && isExpanded && isMobile) {
      setIsExpanded(false);
    }
  }, [mobileMenuContext?.isMobileMenuOpen, isMobile]);

  // 打开 Header 菜单时，关闭 Sidebar
  const handleHeaderToggle = () => {
    const newState = !isExpanded;
    setIsExpanded(newState);
    if (newState && mobileMenuContext?.isMobileMenuOpen && isMobile) {
      mobileMenuContext.setIsMobileMenuOpen(false);
    }
  };

  // Tooltip 文案
  const tooltips = {
    themeMode: {
      light: { en: 'Switch to Dark Mode', zh: '切换至深色模式' },
      dark: { en: 'Switch to Light Mode', zh: '切换至浅色模式' }
    },
    themeColor: { en: 'Theme Color', zh: '主题颜色' },
    language: { en: 'Switch Language', zh: '切换语言' },
    apiKey: { en: 'API Key Settings', zh: 'API 密钥设置' },
    pubmed: { en: 'Visit PubMed', zh: '访问PubMed' }
  };

  // 包装函数：点击后收起菜单
  const handleActionAndClose = (action: () => void) => {
    action();
    if (isMobile) {
      setIsExpanded(false);
    }
  };

  return (
    <>
      {/* 移动端遮罩层 */}
      {isMobile && isExpanded && (
        <div className="header-overlay" onClick={() => setIsExpanded(false)}></div>
      )}
      <header className={`top-header ${isMobile ? 'mobile' : ''}`}>
        <MobileMenuButton />
        {isMobile && (
          <button
            className="header-toggle-btn"
            onClick={handleHeaderToggle}
            aria-label={isExpanded ? 'Collapse header' : 'Expand header'}
          >
            {isExpanded ? <CaretUp size={20} /> : <CaretDown size={20} />}
          </button>
        )}
        <div className={`header-right ${isMobile ? 'mobile-menu' : ''} ${isMobile && isExpanded ? 'mobile-open' : ''}`}>
          {/* Theme Mode Toggle */}
          <button
            className="icon-btn"
            onClick={() => handleActionAndClose(toggleMode)}
            data-tooltip={theme.mode === 'light' ? tooltips.themeMode.light[theme.language] : tooltips.themeMode.dark[theme.language]}
          >
            {theme.mode === 'light' ? <Sun size={20} /> : <Moon size={20} />}
            {isMobile && <span className="mobile-label">{theme.mode === 'light' ? (theme.language === 'zh' ? '深色模式' : 'Dark Mode') : (theme.language === 'zh' ? '浅色模式' : 'Light Mode')}</span>}
          </button>

          {/* Theme Color Picker */}
          <button
            className="icon-btn"
            onClick={() => handleActionAndClose(() => setColorModalOpen(true))}
            data-tooltip={tooltips.themeColor[theme.language]}
          >
            <Palette size={20} />
            {isMobile && <span className="mobile-label">{theme.language === 'zh' ? '主题颜色' : 'Theme Color'}</span>}
          </button>

          {/* Theme Color Modal */}
          <ThemeColorModal
            isOpen={colorModalOpen}
            onClose={() => setColorModalOpen(false)}
          />

          {/* Language Toggle */}
          <button className="icon-btn lang-toggle-btn" onClick={() => handleActionAndClose(toggleLanguage)} data-tooltip={tooltips.language[theme.language]}>
            <Translate size={20} />
            {isMobile && <span className="mobile-label">{theme.language === 'zh' ? '切换语言' : 'Switch Language'}</span>}
          </button>



          {/* API Key
          <button className="icon-btn" onClick={() => handleActionAndClose(() => { })} data-tooltip={tooltips.apiKey[theme.language]}>
            <Key size={20} />
            {isMobile && <span className="mobile-label">{theme.language === 'zh' ? 'API密钥' : 'API Key'}</span>}
          </button> */}

          {/* GitHub Link */}
          {/* <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="icon-btn"
          title="GitHub Repository"
        >
          <GithubLogo size={20} />
        </a> */}

          {/* User Avatar */}
          {/* <button className="user-avatar" title="User Profile">
          <img src={user?.avatar || `src/images/profiles/manProfile.jpg`} alt="User" />
        </button> */}

          {/* PubMed Link */}
          <a
            href="https://pubmed.ncbi.nlm.nih.gov"
            target="_blank"
            rel="noopener noreferrer"
            className="icon-btn"
            onClick={() => isMobile && setIsExpanded(false)}
            data-tooltip={tooltips.pubmed[theme.language]}
          >
            <NihIcon size={20} />
            {isMobile && <span className="mobile-label">PubMed</span>}
          </a>
        </div>
      </header>
    </>
  );
};

