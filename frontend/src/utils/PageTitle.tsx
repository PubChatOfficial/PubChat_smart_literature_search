import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

// 路由到标题的映射
const routeTitleMap: Record<string, string> = {
  '/': ' - Home',
  '/search/task': ' - Search',
  '/search/result': ' - Search',
  '/review': ' - Review',
  '/review/task': ' - Review',
  '/review/result': ' - Review',
  '/search-review': ' - Search & Review',
  '/search-review/task': ' - Search & Review',
  '/search-review/result': ' - Search & Review',
  '/alerts': ' - Alerts',
  '/use-cases': ' - Use Cases',
  '/files': ' - Recent Files',
  '/account': ' - My Account',
  '/contactus': ' - Contact Us',
  '/roastme': ' - Roast Me',
  '/login': ' - Login',
  '/register': ' - Register',
  '/forgetPassword': ' - Reset Password',
};

export const PageTitle: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    // 获取当前路径对应的标题
    const pageTitle = routeTitleMap[location.pathname] || '';
    
    // 更新 document.title
    document.title = `PubChat${pageTitle}`;
  }, [location.pathname]);

  return null; // 这个组件不渲染任何内容
};

