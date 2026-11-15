import { BrowserRouter, Route, Routes } from 'react-router'
import { AccountPage } from './accounts/AccountPage'
import { AuthProvider, RequireAuth } from './accounts/auth'
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
      <AuthProvider>
        <Routes>
          {/* Open to all: the demo when logged out, live calls once logged in. */}
          <Route path="/" element={<LandingPage />} />
          {/* Behind the login. */}
          <Route path="/evidence" element={<RequireAuth><EvidencePage /></RequireAuth>} />
          <Route path="/home" element={<RequireAuth><HomePage /></RequireAuth>} />
          <Route path="/wordmark" element={<RequireAuth><WordmarkPage /></RequireAuth>} /> {/* temporary: pick a split */}
          <Route path="/account" element={<AccountPage />} />
          {/* Never behind a login: Grandma's laptop is paired once, and the family phone opens the
              per-call alert link, which carries its own token. */}
          <Route path="/elder" element={<ElderScreen />} />
          <Route path="/family" element={<FamilyPage />} />
          <Route path="/pair" element={<PairPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
