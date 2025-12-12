import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from './services/api'
import { useStore } from './hooks/useStore'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  const { setPersonalities, setActivePersonality, activePersonality } = useStore()

  // Fetch personalities on mount
  const { data: personalities } = useQuery({
    queryKey: ['personalities'],
    queryFn: () => api.listPersonalities(),
  })

  // Fetch active personality
  const { data: active } = useQuery({
    queryKey: ['activePersonality'],
    queryFn: () => api.getActivePersonality(),
    enabled: !activePersonality,
  })

  useEffect(() => {
    if (personalities) {
      setPersonalities(personalities)
    }
  }, [personalities, setPersonalities])

  useEffect(() => {
    if (active && !activePersonality) {
      setActivePersonality(active)
    }
  }, [active, activePersonality, setActivePersonality])

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}

export default App
