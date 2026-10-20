import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import './i18n' // Import i18n configuration
import { applyTheme, getInitialTheme, watchSystemTheme } from './lib/theme'

applyTheme(getInitialTheme())
watchSystemTheme(() => applyTheme(getInitialTheme()))

ReactDOM.createRoot(document.getElementById('root')!).render(
  // <React.StrictMode>
    <App />
  // </React.StrictMode>,
)
