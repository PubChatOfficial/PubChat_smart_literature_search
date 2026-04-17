import React, { useState, useEffect, createContext, useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { SidebarSimple, MagnifyingGlass, ClockClockwise, List, X } from '@phosphor-icons/react';
import { useTheme } from '@/utils/ThemeContext';
import { Cookies } from '@/utils/cookies';
import { Logo } from '@/icons/logo';
import { LogoFont } from '@/icons/logo_font';
import '@/styles/global.css';
import './SideBar.css';

interface NavItem {
  key: string;
  icon: React.ReactNode;
  label: { en: string; zh: string };
  href: string;
  active?: boolean;
}

const navItems: NavItem[] = [
  { key: 'literatureSearch', icon: <MagnifyingGlass />, label: { en: 'Literature Search', zh: '文献检索' }, href: '/search' },
  { key: 'recentFiles', icon: <ClockClockwise />, label: { en: 'Download Files', zh: '文件下载' }, href: '/files' }
];

// 创建移动端菜单上下文
interface MobileMenuContextType {
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (open: boolean) => void;
}

const MobileMenuContext = createContext<MobileMenuContextType | null>(null);

export const useMobileMenu = () => {
  const context = useContext(MobileMenuContext);
  return context;
};

export const Sidebar: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  // 检测是否为移动端
  const isMobile = () => window.innerWidth <= 900;
  const [isMobileDevice, setIsMobileDevice] = useState(isMobile());
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [collapsed, setCollapsed] = useState(() => {
    // Check if user has manually set collapsed state
    const saved = Cookies.getSidebarCollapsed();
    if (saved !== null) return saved;
    // Default to collapsed
    return true;
  });

  useEffect(() => {
    const handleResize = () => {
      setIsMobileDevice(isMobile());
      if (!isMobile()) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);


  const handleToggle = () => {
    const newCollapsed = !collapsed;
    setCollapsed(newCollapsed);
    Cookies.setSidebarCollapsed(newCollapsed);
  };

  const handleLogoClick = () => {
    if (collapsed) {
      setCollapsed(false);
      Cookies.setSidebarCollapsed(false);
    }
  };

  const handleNavItemClick = (href: string) => {
    navigate(href);
    if (isMobileDevice) {
      setMobileMenuOpen(false);
    }
  };

  // 在body上添加类来控制按钮显示
  useEffect(() => {
    if (isMobileDevice && mobileMenuOpen) {
      document.body.classList.add('mobile-menu-open');
    } else {
      document.body.classList.remove('mobile-menu-open');
    }
    return () => {
      document.body.classList.remove('mobile-menu-open');
    };
  }, [isMobileDevice, mobileMenuOpen]);

  // 动态更新 CSS 变量以支持 Toast 居中（初始化和状态变化时）
  useEffect(() => {
    const root = document.documentElement;
    if (collapsed) {
      root.style.setProperty('--sidebar-width', '56px');
    } else {
      root.style.setProperty('--sidebar-width', '190px');
    }
  }, [collapsed]);

  return (
    <MobileMenuContext.Provider value={{ isMobileMenuOpen: mobileMenuOpen, setIsMobileMenuOpen: setMobileMenuOpen }}>
      {/* 移动端遮罩层 */}
      {isMobileDevice && mobileMenuOpen && (
        <div className="sidebar-overlay" onClick={() => setMobileMenuOpen(false)}></div>
      )}

      <aside
        className={`sidebar ${collapsed ? 'collapsed' : ''} ${isMobileDevice ? 'mobile' : ''} ${isMobileDevice && mobileMenuOpen ? 'mobile-open' : ''}`}
        onClick={collapsed && !isMobileDevice ? handleToggle : undefined}
      >
        <div className="logo-area">
          {/* Logo component - shown by default, hidden on sidebar hover when expanded */}
          <Logo
            className="logo-img"
            onClick={collapsed ? handleLogoClick : undefined}
            data-tooltip={collapsed ? (theme.language === 'en' ? 'Expand Sidebar' : '展开侧边栏') : undefined}
          />

          {/* Toggle icon - hidden by default, shown on sidebar hover */}
          <div
            className="logo-collapse-icon"
            onClick={handleToggle}
            data-tooltip={collapsed ? (theme.language === 'en' ? 'Expand Sidebar' : '展开侧边栏') : (theme.language === 'en' ? 'Collapse Sidebar' : '收起侧边栏')}
          >
            <SidebarSimple size={24} mirrored={collapsed} />
          </div>

          {!isMobileDevice && (
            <>
              <LogoFont className="logo-text" width={93} color={theme.primaryColor} />
              {/* <button className="sidebar-toggle" onClick={handleToggle} title="Collapse Sidebar">
                <SidebarSimple size={20} />
              </button> */}
            </>
          )}
          {isMobileDevice && (
            <>
              <LogoFont className="logo-text" width={93} color={theme.primaryColor} />
              <button className="mobile-close-button" onClick={() => setMobileMenuOpen(false)} title={theme.language === 'en' ? 'Close Menu' : '关闭菜单'}>
                <X size={20} />
              </button>
            </>
          )}
        </div>

        <nav className="nav-menu">
          {navItems.map((item) => {
            // 判断当前路径是否激活该导航项
            let isActive = location.pathname === item.href;

            // Literature Search (Home) checks for / or /search/ sub-paths
            if (item.key === 'literatureSearch') {
              isActive = location.pathname === '/search' || location.pathname.startsWith('/search/');
            }

            return (
              <button
                key={item.key}
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={(e) => {
                  e.stopPropagation(); // 阻止事件冒泡，防止触发 sidebar 的点击事件
                  handleNavItemClick(item.href);
                }}
                data-tooltip={item.label[theme.language]} // 用于 CSS tooltip
              >
                {item.icon}
                <span>{item.label[theme.language]}</span>
              </button>
            );
          })}
        </nav>
      </aside>
      {children}
    </MobileMenuContext.Provider>
  );
};

// 移动端菜单按钮组件
export const MobileMenuButton: React.FC = () => {
  const context = useMobileMenu();

  if (!context) return null;

  return (
    <button
      className="mobile-menu-button"
      onClick={() => context.setIsMobileMenuOpen(!context.isMobileMenuOpen)}
      aria-label="Toggle Menu"
    >
      <List size={20} weight="bold" />
    </button>
  );
};
