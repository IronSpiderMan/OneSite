import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import './i18n' // Import i18n configuration
import { applyTheme, getInitialStyle, getInitialMode, watchSystemTheme } from './lib/theme'

applyTheme(getInitialStyle(), getInitialMode())
watchSystemTheme(() => applyTheme(getInitialStyle(), getInitialMode()))

ReactDOM.createRoot(document.getElementById('root')!).render(
  // <React.StrictMode>
    <App />
  // </React.StrictMode>,
)
