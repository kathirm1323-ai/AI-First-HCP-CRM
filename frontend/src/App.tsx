import { useEffect } from 'react'
import { useAppDispatch } from './hooks'
import { loadDashboard } from './store/crmSlice'
import { InteractionForm } from './components/InteractionForm'
import { ChatPanel } from './components/ChatPanel'

export default function App() {
  const dispatch = useAppDispatch()
  useEffect(() => { dispatch(loadDashboard()) }, [dispatch])

  return <main className="app-shell">
    <section className="log-workspace" aria-label="Log HCP interaction">
      <InteractionForm />
      <ChatPanel />
    </section>
  </main>
}