import { BrowserRouter, Link, Route, Routes } from 'react-router'
import { EventLog } from './routes/EventLog'

function Home() {
  return (
    <main>
      <h1>Aegis</h1>
      <ul>
        <li><Link to="/elder?fixture=scam-grandson">/elder</Link> (scam sample)</li>
        <li><Link to="/elder?fixture=benign-party">/elder</Link> (normal call sample)</li>
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
        <Route path="/elder" element={<EventLog title="Elder" role="elder" />} />
        <Route path="/family" element={<EventLog title="Family" role="family" />} />
        <Route path="/evidence" element={<EventLog title="Evidence" role="elder" />} />
      </Routes>
    </BrowserRouter>
  )
}
