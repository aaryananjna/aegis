import { BrowserRouter, Link, Route, Routes } from 'react-router'
import { ElderScreen } from './elder/ElderScreen'
import { EvidencePage } from './evidence/EvidencePage'
import { FamilyPage } from './family/FamilyPage'

function Home() {
  return (
    <main>
      <h1>Aegis</h1>
      <ul>
        <li><Link to="/elder?fixture=scam-grandson">/elder</Link> (scam sample)</li>
        <li><Link to="/elder?fixture=benign-party">/elder</Link> (normal call sample)</li>
        <li><Link to="/elder?fixture=demo-bank">/elder</Link> (fake bank sample)</li>
        <li><Link to="/family?fixture=scam-grandson">/family</Link> (scam sample)</li>
        <li><Link to="/evidence?fixture=scam-grandson">/evidence</Link> (scam sample)</li>
      </ul>
    </main>
  )
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/elder" element={<ElderScreen />} />
        <Route path="/family" element={<FamilyPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
      </Routes>
    </BrowserRouter>
  )
}
