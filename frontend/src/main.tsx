import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { getTheme, applyTheme } from './lib/theme.ts'

// Apply the persisted theme (defaults to dark).
applyTheme(getTheme());

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
