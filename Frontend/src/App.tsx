import { useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Header, MainLayout, MainPane, MobileSidebar, Sidebar } from './components/layout/Sidebar'
import AudioAnalysis from './pages/AudioAnalysis'
import FailureReports from './pages/FailureReports'
import Landing from './pages/Landing'
import Overview from './pages/Overview'
import ScenarioLab from './pages/ScenarioLab'
import Settings from './pages/Settings'
import TestExecution from './pages/TestExecution'

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [entered, setEntered] = useState(false)

  if (!entered) return <Landing onEnter={() => setEntered(true)} />

  return (
    <MainLayout>
      <MobileSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <Sidebar />
      <MainPane>
        <Header toggleSidebar={() => setSidebarOpen(true)} />
        <div className="no-scrollbar min-h-0 flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/scenario-lab" element={<ScenarioLab />} />
            <Route path="/test-execution" element={<TestExecution />} />
            <Route path="/audio-analysis" element={<AudioAnalysis />} />
            <Route path="/failure-reports" element={<FailureReports />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </MainPane>
    </MainLayout>
  )
}
