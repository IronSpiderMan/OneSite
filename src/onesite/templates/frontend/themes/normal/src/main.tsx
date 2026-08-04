import React from 'react'
import ReactDOM from 'react-dom/client'
import 'antd/dist/reset.css'
import App from './App.tsx'
import './index.css'
import './i18n'
import { AntdThemeProvider } from './components/AntdThemeProvider'
import { applyTheme, getInitialStyle, getInitialMode, watchSystemTheme } from './lib/theme'

applyTheme(getInitialStyle(), getInitialMode())
watchSystemTheme(() => applyTheme(getInitialStyle(), getInitialMode()))

ReactDOM.createRoot(document.getElementById('root')!).render(
  <AntdThemeProvider>
    <App />
  </AntdThemeProvider>,
)
