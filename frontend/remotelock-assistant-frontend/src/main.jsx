import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// import App from './App.jsx' // Old app
import AppNew from './AppNew.jsx' // New redesigned app

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AppNew />
  </StrictMode>,
)
