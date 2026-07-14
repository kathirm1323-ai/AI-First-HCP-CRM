import { useEffect } from 'react'
import { useAppDispatch, useAppSelector } from './hooks'
import { loadDashboard } from './store/crmSlice'
import { InteractionForm } from './components/InteractionForm'
import { ChatPanel } from './components/ChatPanel'
import { ModeToggle } from './components/ModeToggle'

export default function App() {
  const dispatch = useAppDispatch()
  const mode = useAppSelector(s => s.crm.mode)
  useEffect(() => { dispatch(loadDashboard()) }, [dispatch])

  return <main className="app-shell">
    <header className="workspace-toolbar"><div><span className="section-kicker">FIELD ENGAGEMENT</span><h1>Log HCP Interaction</h1></div><ModeToggle /></header>
    <section className={`log-workspace mode-${mode}`} aria-label="Log HCP interaction">
      {mode === 'form' ? <InteractionForm /> : <ChatPanel />}
    </section>
  </main>
}