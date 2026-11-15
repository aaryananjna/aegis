import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { applySavedTheme } from './brand/ThemeToggle'
// Playfair Display (headings) ships with the app: no Google Fonts, works offline on the hotspot.
import '@fontsource/playfair-display/700.css'
import './index.css'

applySavedTheme()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
