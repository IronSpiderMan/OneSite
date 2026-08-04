import React, { useEffect, useState } from 'react';
import { App, ConfigProvider, theme } from 'antd';
import enUS from 'antd/locale/en_US';
import zhCN from 'antd/locale/zh_CN';

export const AntdThemeProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  const language = localStorage.getItem('custom_config_language') || 'en';

  useEffect(() => {
    const root = document.documentElement;
    const observer = new MutationObserver(() => setDark(root.classList.contains('dark')));
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  return (
    <ConfigProvider
      locale={language === 'zh' ? zhCN : enUS}
      componentSize="middle"
      theme={{
        algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        cssVar: {},
        token: {
          colorPrimary: '#409eff',
          colorInfo: '#409eff',
          colorSuccess: '#67c23a',
          colorWarning: '#e6a23c',
          colorError: '#f56c6c',
          borderRadius: 4,
          controlHeight: 32,
          fontSize: 14,
          colorBgLayout: dark ? '#0f1115' : '#f5f7fa',
          colorBgContainer: dark ? '#181a1f' : '#ffffff',
        },
        components: {
          Button: { defaultShadow: 'none', primaryShadow: 'none' },
          Card: { bodyPadding: 20, headerHeight: 48 },
          Table: { headerBg: dark ? '#20232a' : '#f5f7fa', headerColor: dark ? '#cfd3dc' : '#606266' },
          Modal: { borderRadiusLG: 4 },
        },
      }}
    >
      <App>{children}</App>
    </ConfigProvider>
  );
};
