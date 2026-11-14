import { BrowserRouter, Route, Routes } from 'react-router'
import { AccountPage } from './accounts/AccountPage'
import { WordmarkPage } from './brand/WordmarkPage'
import { HomePage } from './accounts/HomePage'
import { PairPage } from './accounts/PairPage'
import { ElderScreen } from './elder/ElderScreen'
import { EvidencePage } from './evidence/EvidencePage'
import { FamilyPage } from './family/FamilyPage'
import { LandingPage } from './landing/LandingPage'

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/elder" element={<ElderScreen />} />
        <Route path="/family" element={<FamilyPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/pair" element={<PairPage />} />
        <Route path="/wordmark" element={<WordmarkPage />} /> {/* temporary: pick a split */}
      </Routes>
    </BrowserRouter>
  )
}
